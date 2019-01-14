#coding=utf-8
################################
# linux server : Redhat 7
# win server : server 2008
# 
# UPDATE BY JDZYH, 2019/1/14 
################################
import netsnmp
import time
import datetime
import struct
################################
# Basic Server Class
################################
class basicServerClass(object):
    def __init__(self, type, dest_ip, time, program_name_list=[], Version=2, Community='public'):
        self.type = type
        self.dest_ip = dest_ip
        self.Version = Version
        self.Community = Community
        self.time = time
        self.program_name_list = program_name_list
        self.DEFAULT_MEM_DESCR = ['Physical memory', 'Memory buffers', 'Cached memory', 'Virtual memory', 'Swap space', 'Virtual Memory', 'Physical Memory']
        
        self.sysDescr =self.get_sysDescr()
        self.uptime = self.get_uptime()
        self.date = self.get_hrSystemDate()
        self.cpu_max = max(map(int, self.get_cpuUsed()))
        self.mem_status, self.partition_status = self.get_diskStatus()
        self.processList = self.get_processList()
    #===============================================
    # Interface : Return Final Result.
    #===============================================  
    # default return function
    # must @Override by subclass
    def get_all_status(self):
        status = {'time':self.time,
                    'type':self.type,
                    'descr':self.sysDescr,
                    'ip':self.dest_ip, 
                    'uptime':self.uptime, #Days
                    'date':self.date,
                    'cpu':self.cpu_max,
                    'mem':self.mem_status, #Bytes, {'hrStorageDescr1': hrStorageSize}
                    'partition':self.partition_status, #Bytes, [{'hrStorageDescr1': hrStorageSize}]
                    'process':self.processList #[{'pid':pid, 'hrSWRunName':hrSWRunName, 'hrSWRunPath':hrSWRunPath, 'hrSWRunParameters':hrSWRunParameters}, ...]
                }
        return status 

    #===============================================
    # Common Tools
    #===============================================    
    def kb_to_gb(self, number):
        return round(float(number)/1024/1024,1)
    
    def b_to_gb(self, number):
        return round(float(number)/1024/1024/1024,1)
        
    def snmpget(self, oid):
        return netsnmp.snmpget(oid,
                               Version=self.Version,
                               DestHost=self.dest_ip,
                               Community=self.Community)
    def snmpwalk(self, oid):
        return netsnmp.snmpwalk(oid,
                               Version=self.Version,
                               DestHost=self.dest_ip,
                               Community=self.Community)
    # Get bulk
    def snmpgetbulk(self, oid_tag):
        ret = {}
        oid = oid_tag
        oid_append = 0
        
        sess = netsnmp.Session(Version=self.Version, DestHost=self.dest_ip, Community=self.Community)
        while True:
            cur_oid = oid + '.' + str(oid_append)
            
            varlist = netsnmp.VarList(netsnmp.Varbind(cur_oid))
            
            # This iteration got nothing, return.
            if not sess.getbulk(0, 100, varlist):
                return ret
            
            for v in varlist:
                # We have got all oid_tag's OIDs, return. 
                if not v.tag.startswith(oid):
                    return ret
                
                oid_append = v.iid
                ret[v.iid] = v.val
    #===============================================
    # OS Infos
    #===============================================
    def get_sysDescr(self):
        oid = netsnmp.Varbind('sysDescr.0')
        snmp_valid = self.snmpget(oid)
        return snmp_valid[0]

    # timetick unit : 10 ms
    # 1s = 1000ms = unit(10ms) * 100
    # Retrun xx days
    def get_uptime(self):
        oid = netsnmp.Varbind('.1.3.6.1.2.1.25.1.1.0')
        uptime = self.snmpget(oid)
        return int(uptime[0])/86400/100

    def get_hrSystemDate(self):
        oid = netsnmp.Varbind('hrSystemDate.0')
        now = datetime.datetime.now()
        date = self.snmpget(oid)
        if date[0] is None:
            print 'Faile to get date !!!'
            return 'ERROR'
        else:
            date = datetime.datetime(*struct.unpack('>HBBBBBB', date[0][0:8]))
            return abs(date - now)

    def get_cpuUsed(self):
        cpuUsed_oid = netsnmp.Varbind('.1.3.6.1.2.1.25.3.3.1.2')
        cpuUsed = self.snmpwalk(cpuUsed_oid)
        return cpuUsed
    
    #===============================================
    # Menmory And Harddisk
    #===============================================
    # 
    def get_hrStorageDescrList(self):
        hrStorageDescr_oid = netsnmp.Varbind('.1.3.6.1.2.1.25.2.3.1.3')
        hrStorageDescrList = self.snmpwalk(hrStorageDescr_oid)
        return hrStorageDescrList
   
    # 
    def get_hrStorageAllocationUnits(self):
        hrStorageAllocationUnits_oid = netsnmp.Varbind('.1.3.6.1.2.1.25.2.3.1.4')
        hrStorageAllocationUnits = self.snmpwalk(hrStorageAllocationUnits_oid)
        return hrStorageAllocationUnits

    # 
    def get_hrStorageSizeList(self):
        hrStorageSize_oid = netsnmp.Varbind('.1.3.6.1.2.1.25.2.3.1.5')
        hrStorageSizeList = self.snmpwalk(hrStorageSize_oid)
        return hrStorageSizeList

    # 
    def get_hrStorageUsedList(self):
        hrStorageUsed_oid = netsnmp.Varbind('.1.3.6.1.2.1.25.2.3.1.6')
        hrStorageUsedList = self.snmpwalk(hrStorageUsed_oid)
        return hrStorageUsedList
    
    # return two dict (mem_status, partition_status) 
    # size unit : Byte
    # mem_status : Bytes, {'hrStorageDescr1': hrStorageSize}
    # partition_status : Bytes, [{'hrStorageDescr1': hrStorageSize}]
    # 
    def get_diskStatus(self):
        hrStorageDescrList = self.get_hrStorageDescrList()
        hrStorageAllocationUnits = self.get_hrStorageAllocationUnits()
        hrStorageSizeList = self.get_hrStorageSizeList()
        hrStorageUsedList = self.get_hrStorageUsedList()
        
        partition_number = len(hrStorageDescrList)
        
        mem_status = {}
        partition_status = []
        
        for i in range(partition_number):
            if hrStorageSizeList[i]=='0':
                continue
            else:
                hrStorageSize = int(hrStorageSizeList[i]) * int(hrStorageAllocationUnits[i])
                hrStorageUsed = int(hrStorageUsedList[i]) * int(hrStorageAllocationUnits[i])
                
                if hrStorageDescrList[i] in self.DEFAULT_MEM_DESCR:
                    mem_status['ip'] = self.dest_ip
                    mem_status['time'] = self.time
                    mem_status[hrStorageDescrList[i].lower()+'-used'] = hrStorageUsed
                    mem_status[hrStorageDescrList[i].lower()+'-total'] = hrStorageSize
                else:
                    partition = {}
                    partition['time'] = self.time
                    partition['ip'] = self.dest_ip
                    partition['descr'] = hrStorageDescrList[i]
                    partition['used'] = hrStorageUsed
                    partition['total'] = hrStorageSize
                    partition_status.append(partition)
            
        return mem_status, partition_status

    #===============================================
    # Program Process
    #===============================================    
    def get_pidDict(self):
        pidDict = self.snmpgetbulk('hrSWRunIndex')
        return pidDict
    #    
    def get_hrSWRunNameDict(self):
        hrSWRunNameDict = self.snmpgetbulk('hrSWRunName')
        return hrSWRunNameDict
    
    # transfer to utf-8
    def get_hrSWRunPathDict(self):
        hrSWRunPathDict = self.snmpgetbulk('hrSWRunPath') 
        
        result = {}
        for iid, val in hrSWRunPathDict.iteritems():
            if val:
                result[iid] = val.decode('GBK').encode('utf8')
            else:
                result[iid] = ''
        return result
        
    def get_hrSWRunParametersDict(self):
        hrSWRunParametersDict = self.snmpgetbulk('hrSWRunParameters')
        return hrSWRunParametersDict
    # KB
    def get_hrSWRunPerfMemDict(self):
        hrSWRunPerfMemDict = self.snmpgetbulk('hrSWRunPerfMem')
        return hrSWRunPerfMemDict
    
    #cpu_per_second = (perfcpu1 - perfcpu2) / (t1 - t2) % 
    def get_hrSWRunPerfCPUDict(self):
        hrSWRunPerfCPUDict_1 = self.snmpgetbulk('hrSWRunPerfCPU')
        #
        time.sleep(1)
        hrSWRunPerfCPUDict_2 = self.snmpgetbulk('hrSWRunPerfCPU')
        #
        hrSWRunPerfCPUDict={}
        for iid, val in hrSWRunPerfCPUDict_1.iteritems():
            if(iid in hrSWRunPerfCPUDict_2.keys()):
                hrSWRunPerfCPUDict[iid] = int(hrSWRunPerfCPUDict_2[iid]) - int(hrSWRunPerfCPUDict_1[iid])
        return hrSWRunPerfCPUDict

		
    def get_my_pids(self, pid_dict, src_dict):
        for iid, val in src_dict.iteritems():
            for program_name in self.program_name_list:					
                if val and program_name in val:
                    pid_dict[iid] = 1     

        
    def get_processList(self):
        if len(self.program_name_list)==0:
            return []

        #pidDict = self.get_pidDict()
        hrSWRunNameDict = self.get_hrSWRunNameDict()
        hrSWRunPathDict = self.get_hrSWRunPathDict()
        hrSWRunParametersDict = self.get_hrSWRunParametersDict()
        hrSWRunPerfMemDict = self.get_hrSWRunPerfMemDict()
        hrSWRunPerfCPUDict = self.get_hrSWRunPerfCPUDict()        
        
        process_list = []

        pid_dict = {}
        if 'linux'==self.type:
            self.get_my_pids(pid_dict, hrSWRunParametersDict)
            self.get_my_pids(pid_dict, hrSWRunNameDict)
        elif 'windows'==self.type:
            self.get_my_pids(pid_dict, hrSWRunParametersDict)
            self.get_my_pids(pid_dict, hrSWRunNameDict)
        
        for iid in pid_dict.keys():               
            process = {
                'time':self.time,
                'ip':self.dest_ip,
                'pid':iid, 
                'hrSWRunName'.lower():hrSWRunNameDict[iid] if iid in hrSWRunNameDict.keys() else '', 
                'hrSWRunPath'.lower():hrSWRunPathDict[iid] if iid in hrSWRunPathDict.keys() else '', 
                'hrSWRunParameters'.lower():hrSWRunParametersDict[iid] if iid in hrSWRunParametersDict.keys() else '',
                'hrSWRunPerfMem'.lower():hrSWRunPerfMemDict[iid] if iid in hrSWRunPerfMemDict.keys() else '',
                'hrSWRunPerfCPU'.lower():hrSWRunPerfCPUDict[iid] if iid in hrSWRunPerfCPUDict.keys() else '' 
            }
            process_list.append(process)
        return process_list
    #===============================================
    # TODO:Others
    #===============================================


################################
# Windows Server Class
################################
class winServerClass(basicServerClass):
    def __init__(self, type, dest_ip, time, program_name_list, Version=2, Community='public'):
        basicServerClass.__init__(self, type, dest_ip, time, program_name_list, Version=2, Community='public')

    # reshape all status
    # @Override
    def get_all_status(self):
        # Windows Only Needs Physical Memory
        self.mem_status['program memory-used'] = self.mem_status['physical memory-used']
        status = basicServerClass.get_all_status(self)
        return status

################################
# Linux Server Class
################################
class linuxServerClass(basicServerClass):
    def __init__(self, type, dest_ip, time, program_name_list, Version=2, Community='public'):
        basicServerClass.__init__(self, type, dest_ip, time, program_name_list, Version=2, Community='public')
    
    # mem = xxx Byte
    def get_memTotalReal(self):
        return self.mem_status['physical memory-total']
   
    # mem = xxx Byte
    def get_memUsedReal(self):
        return self.mem_status['physical memory-used']

    # mem = xxx Byte
    def get_memBuffer(self):
        return self.mem_status['memory buffers-used']

    # mem = xxx Byte
    def get_memCached(self):
        return self.mem_status['cached memory-used']

    # mem = xxx Byte
    def get_memProgmUsed(self):
        memProgmUsed = self.get_memUsedReal() - self.get_memBuffer() - self.get_memCached()
        return memProgmUsed
    
    # @Override
    def get_all_status(self):
        # Linux Needs To Calculate Program used Mem.
        self.mem_status['program memory-used'] = self.get_memProgmUsed()
        status = basicServerClass.get_all_status(self) 
        return status
