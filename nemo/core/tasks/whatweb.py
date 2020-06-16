#!/usr/bin/env python3
# coding:utf-8
import re
import subprocess
from multiprocessing.dummy import Pool
from .taskbase import TaskBase
from nemo.common.utils.config import load_config
from nemo.common.utils.iputils import check_ip_or_domain


class WhatWeb(TaskBase):
    '''调用WhatWeb的获取CMS的指纹
    参数:options  
            {   
                'target':   [url1,url2,ur3...],url列表可是以doamin或IP:PORT，如www.cq.sgcc.com.cn 或 58.17.138.70:80
                'org_id':   id,target关联的组织机构ID
            }
    任务结果:
        保存为ip或domain资产格式的列表：
        [{'ip':'192.168.1.1','port':[{'port':80,'whatweb':'xxx,yyy,zzz','source':'whatweb'},...]},...]
        [{'domain':'www.cq.sgcc.com.cn','whatweb':'xxx,yyy,zzz'},...]
    '''

    def __init__(self):
        super().__init__()

        # 任务名称
        self.task_name = 'whatweb'
        # 任务描述
        self.task_description = '调用whatweb获取CMS指纹'
        # 参数
        self.org_id = None
        self.source = 'whatweb'
        self.result_attr_keys = ('whatweb', )
        self.threads = 10
        # 默认的参数
        self.target = []
        config_jsondata = load_config()
        self.whatweb_bin = config_jsondata['whatweb']['bin']

    def __exe_whatweb(self, url):
        '''调用nmap对指定IP和端口进行扫描
        '''
        whatweb_bin = [self.whatweb_bin, '-q', '--color=never', '--log-brief', '-',
                       '-U=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/52.0.2743.116 Safari/537.36 Edge/15.15063',
                       url]
        # 调用whatweb进行扫描
        try:
            child = subprocess.Popen(whatweb_bin, stdout=subprocess.PIPE)
            # 读取扫描结果
            scan_result = []
            while child.poll() is None:
                line = child.stdout.readline().decode()
                scan_result.append(line)
            # 解析nmap扫描结果
            result = ''.join(scan_result)
            
            if result.startswith('ERROR'):
                result = None
        except FileNotFoundError as e:
            result = None
            print(e)
        except:
            result = None
            print(e)

        return result

    def prepare(self, options):
        '''解析参数
        '''
        # 将 [url1,url2,ur3...]格式处理为ip和domain表的格式
        target_list = []
        for t in options['target']:
            u = t.split(':')
            port = u[1] if len(u) == 2 else 80
            # IP地址
            if check_ip_or_domain(u[0]):
                for i in target_list:
                    if 'ip' in i and 'port' in i and i['ip'] == u[0]:
                        i['port'].append({'port': port})
                        break
                else:
                    target_list.append({'ip': u[0], 'port': [{'port': port}]})
            else:
                # 域名
                for d in target_list:
                    if 'domain' in d and d['domain'] == t:
                        break
                else:
                    target_list.append({'domain': t})

        self.target = target_list
        self.org_id = self.get_option('org_id', options, self.org_id)

    def __execute(self, target):
        '''ip参数执行线程
        '''
        # IP:PORT
        if 'ip' in target and 'port' in target:
            for port in target['port']:
                title = self.__exe_whatweb(
                    '{}:{}'.format(target['ip'], port['port']))
                if title:
                    port['whatweb'] = title

        # DOMAIN
        elif 'domain' in target:
                title = self.__exe_whatweb(
                    '{}'.format(target['domain']))
                if title:
                    if 'whatweb' not in target:
                        target['whatweb'] = []
                    target['whatweb'].append(title)

    def execute(self, target_list):
        '''调用what执行扫描任务
        '''
        pool = Pool(self.threads)
        pool.map(self.__execute, target_list)
        pool.close()
        pool.join()

        return target_list

    def run(self, options):
        '''执行任务
        '''
        try:
            self.prepare(options)
            self.execute(self.target)
            result = self.save_ip(self.target)
            result.update(self.save_domain(self.target))
            result['status'] = 'success'

            return result
        except Exception as e:
            return {'status': 'fail', 'msg': str(e)}
