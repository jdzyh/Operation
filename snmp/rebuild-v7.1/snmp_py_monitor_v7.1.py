#coding=utf-8
################################
# linux server : Redhat 7
# win server : server 2008
# 
# UPDATE BY JDZYH, 2019/1/14 
################################
import netsnmp
import socket
import csv
import datetime
from server import basicServerClass, linuxServerClass, winServerClass
##################################
# result writer class
##################################
class ResultWriterCSV(object):
    def __init__(self, result_file='result'):
        self.time = datetime.datetime.now().strftime('%Y%m%d')
        self.result_file_pre = '{0}_{1}'.format(result_file, self.time)
    
    #===============================================
    # Output
    #===============================================     
    def write(self, monitor):        
        # Set CSV tittles
        BASIC_HEADERS = ['time', 'ip', 'type', 'descr', 'uptime', 'cpu','date']
        MEM_HEADERS = ['time', 'ip','program memory-used', 
                    'physical memory-used', 'physical memory-total', 
                    'memory buffers-used', 'memory buffers-total', 
                    'cached memory-used', 'cached memory-total', 
                    'virtual memory-used', 'virtual memory-total', 
                    'swap space-used', 'swap space-total']
        PART_HEADERS = ['time', 'ip', 'descr', 'used', 'total']
        PROCESS_HEADERS = ['time', 'ip', 'pid', 'hrswrunname', 'hrswrunpath', 'hrswrunparameters', 'hrswrunperfcpu', 'hrswrunperfmem']
        
        REPORT_HEADERS = ['time', 'ip', 'type', 'descr', 'uptime','date', 'cpu-%', 'memory-%', 'part-%','feedback']
        
        with open(self.result_file_pre+'_basic.csv', 'w') as basic_output:
            with open(self.result_file_pre+'_mem.csv', 'w') as mem_output:
                with open(self.result_file_pre+'_partition.csv', 'w') as part_output:
                    with open(self.result_file_pre+'_process.csv', 'w') as process_output:
                        with open(self.result_file_pre+'_report.csv', 'w') as report_output:
                            # build writers
                            basic_writer = csv.DictWriter(basic_output, delimiter=',', fieldnames=BASIC_HEADERS)
                            mem_writer = csv.DictWriter(mem_output, delimiter=',', fieldnames=MEM_HEADERS)
                            part_writer = csv.DictWriter(part_output, delimiter=',', fieldnames=PART_HEADERS)
                            process_writer = csv.DictWriter(process_output, delimiter=',', fieldnames=PROCESS_HEADERS)
                            report_writer = csv.DictWriter(report_output, delimiter=',', fieldnames=REPORT_HEADERS)
                        
                            basic_writer.writerow( dict((fn,fn) for fn in BASIC_HEADERS) )
                            mem_writer.writerow( dict((fn,fn) for fn in MEM_HEADERS) )
                            part_writer.writerow( dict((fn,fn) for fn in PART_HEADERS) )
                            process_writer.writerow( dict((fn,fn) for fn in PROCESS_HEADERS) )
                            report_writer.writerow( dict((fn,fn) for fn in REPORT_HEADERS) )
                        
                        
                            writer_dict={'basic_writer':basic_writer,
                                        'mem_writer':mem_writer,
                                        'part_writer':part_writer,
                                        'process_writer':process_writer,
                                        'report_writer':report_writer}
                            # Monitor Interface
                            for server_status in monitor.loop():
                                self.write_status(server_status, writer_dict)
    ###
    # Interface, monitor use this function to write status
    ###
    def write_status(self, server_status, writer_dict):
        # Basic server infos.
        if writer_dict.has_key('basic_writer'):
            basic_status={}
            basic_status['time'] = server_status['time']
            basic_status['ip'] = server_status['ip']
            basic_status['descr'] = server_status['descr']
            basic_status['uptime'] = server_status['uptime']
            basic_status['date'] = server_status['date']
            basic_status['cpu'] = server_status['cpu']
            basic_status['type'] = server_status['type']
            writer_dict['basic_writer'].writerow(basic_status)
        # Memory infos.
        if writer_dict.has_key('mem_writer'):
            writer_dict['mem_writer'].writerow(server_status['mem'])
        # Hard disk infos.
        if writer_dict.has_key('part_writer'):
            for part in server_status['partition']:
                writer_dict['part_writer'].writerow(part)
        # Process infos.
        if writer_dict.has_key('process_writer'):
            for process in server_status['process']:
                writer_dict['process_writer'].writerow(process)
        # Report infos.
        if writer_dict.has_key('report_writer'):
            report_object = {}

            report_object['time'] = server_status['time']
            report_object['ip'] = server_status['ip']
            report_object['type'] = server_status['type']
            report_object['descr'] = server_status['descr']
            report_object['uptime'] = server_status['uptime']
            report_object['date'] = server_status['date']
            report_object['cpu-%'] = server_status['cpu']
            report_object['memory-%'] = round(100.0*server_status['mem']['program memory-used'] / server_status['mem']['physical memory-total'],2)

            ###
            # generate feedback
            CPU_LIMIT=50
            MEM_LIMIT=85
            PART_LIMIT=70
            
            report_object['feedback']=''
            if report_object['cpu-%']>CPU_LIMIT:
                report_object['feedback'] += 'WARN: CPU%>{0}%\r\n'.format(report_object['cpu-%'])
            if report_object['memory-%']>MEM_LIMIT:
                report_object['feedback'] += 'WARN: MEM%>{0}%\r\n'.format(report_object['memory-%'])
            
            # generate partition string
            report_object['part-%'] = ''
            for part in server_status['partition']:
                pctg = round(100.0*part['used'] / part['total'],2)
                report_object['part-%'] +=  '{0}: {1}%.\r\n'.format(part['descr'], pctg)
                
                if pctg>PART_LIMIT:
                    report_object['feedback'] += 'WARN: PART%>{0}%\r\n'.format(pctg)
            
            # Write all status to report.
            writer_dict['report_writer'].writerow(report_object)
##################################
# Main Enter Class
##################################
class MonitorClass(object):
    def __init__(self, hosts_file='hosts', program_name_file='programs', writer=ResultWriterCSV()):
        self.hosts_file = hosts_file
        self.program_name_file = program_name_file
        
        self.writer = writer
        
        self.time = datetime.datetime.now().strftime('%Y%m%d')

    
    #===============================================
    # Output Interface
    #===============================================     
    def process(self):      
        self.writer.write(self)
    
    # Call back function.
    # writer will use this function to loop every server.
    def loop(self):
        program_name_list = self.get_program_name_list()
        host_list = self.get_host_list()
        
        error_log_file = self.writer.result_file_pre+'_log.csv'
        with open(error_log_file, 'w') as log_output:
            
            for ip_address in host_list:
                try:
                    socket.inet_aton(ip_address)
                    server_status = self.get_server_status(ip_address, program_name_list)
                    if len(server_status)==0:
                        print '{0} got no status.'.format(ip_address)
                        continue

                    # 
                    yield server_status
                    
                    print '{0} is done.'.format(ip_address)
                
                except socket.error:
                    socket_error = '{0} is not a valid IP address'.format(ip_address)
                    print socket_error
                    log_output.write(socket_error+'\n')
                    
                except Exception as other_error:
                    print other_error
                    log_output.write('{0} error! {1}'.format(ip_address,str(other_error)))
    #===============================================
    # process
    #===============================================
    def get_program_name_list(self):
        name_list = []
        print 'Load program_name_file:{0}'.format(self.program_name_file)
        with open(self.program_name_file) as file:
            for line in file:
                s = line.strip()
                if len(s)>0:
                    name_list.append(s)
        
        print 'Program_list is :{0}'.format(name_list)
        return name_list
    
    def get_host_list(self):
        host_list = []
        with open(self.hosts_file) as hosts_file:
            for host in hosts_file:
                ip_address = host.strip()
                host_list.append(ip_address)
        return host_list

    def get_sysDescr(self, dest_ip):
        oid = netsnmp.Varbind('sysDescr.0')
        snmp_valid = netsnmp.snmpget(oid, DestHost=dest_ip, Version=2, Community='public')
        
        # return sysdesc and version
        if snmp_valid[0]:
            return snmp_valid[0], 2
        else:
            snmp_valid = netsnmp.snmpget(oid, DestHost=dest_ip, Version=1, Community='public')
            return snmp_valid[0], 1
            
    # Return Dictionary Of servers.    
    def get_server_status(self, dest_ip, program_name_list=[]):
        server_status = {}
        sysDescr, version = self.get_sysDescr(dest_ip)
        if sysDescr:
            print '{0} start...'.format(dest_ip)
            if 'linux' in sysDescr.lower():
                server_status = linuxServerClass('linux', dest_ip, self.time, program_name_list, Version=version).get_all_status()
                #server_status['type'] = 'linux'
                
            elif 'windows' in sysDescr.lower():
                server_status = winServerClass('windows', dest_ip, self.time, program_name_list, Version=version).get_all_status()
                #server_status['type'] = 'windows'
            else:
                print 'UNKNOWN TYPE OF DEVICE. IP:{0} TYPE:{1}'.format(dest_ip, sysDescr)
                server_status = basicServerClass('unknown', dest_ip, self.time, program_name_list, Version=version).get_all_status()
                #server_status['type'] = 'unknown'
        else:
            # Throw Exception Of Not Open SNMP Service.
            ex = Exception('{0} does not open snmp service'.format(dest_ip))
            raise ex

        return server_status

    

################################
# Main Function
################################
if __name__ == '__main__':
    csv_writer = ResultWriterCSV('result')
    monitor = MonitorClass(hosts_file='hosts', writer=csv_writer)
    monitor.process()
