import os
import pandas as pd
import json
import psutil
import platform
import subprocess
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from camera.models import Camera, Camframelog, Survfeatconfig
from django.db.models import F, Func, Value, TextField, CharField
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.db.models import Count
from django.db.models.functions import Cast
from datetime import datetime,timedelta

class Main():
    
    def __init__(self):
        self.res = []
        self.result = []
        self.path = '/opt/paralaxiom/vast/reports_temp/'
    
    def total_camera(self):
        cameras = Camera.objects.values('id', 'CamName')
        result = list(cameras)
        return result
    
    def Intended_Fps(self):
        result = Camera.objects.annotate(
            advanced_setting_value=Func(
                F('AdvancedSettings'),
                Value('8'),
                function='jsonb_extract_path_text',
                output_field=TextField()
            )
        ).filter(Active=True).values('id', 'advanced_setting_value')
        
        return result

    def frame_count(self):
        end_datetime = datetime.now()
        start_datetime = end_datetime - timedelta(minutes=10)
        result = Camframelog.objects.filter(
                    CreationDate__gt=start_datetime,
                    CreationDate__lt=end_datetime
                ).values('CamID_id').annotate(frame_count=Count('*'))
        
        return result
    
    def number_of_checkpoints(self):
        result = (
            Survfeatconfig.objects
                .values('CamID_id', 'MarkingGeometry__0__checkpointType')
                .annotate(NumberOfCheckpoints=Count('*'))
                .filter(Active = True)
                .order_by('CamID_id','MarkingGeometry__0__checkpointType')
                .values('CamID_id', 'MarkingGeometry__0__checkpointType', 'NumberOfCheckpoints')
            )
        
        return result
    
    def hard_frame_count(self):
        result = []
        camera = self.total_camera()
        
        end_datetime = datetime.now()
        start_datetime = end_datetime - timedelta(minutes=10)
        month = str(start_datetime.month)
        if len(month) == 1:
            month = "0"+month
        day = str(start_datetime.day)
        if len(day) == 1:
            day = "0"+day
        dateStr = str(start_datetime.year)+"-"+month+"-"+day
        hour,minute = start_datetime.strftime("%H"),str(int(start_datetime.strftime("%M"))//10-1)
        
        for each in camera:
            curr = {}
            finalAddress = f'ls /opt/paralaxiom/vast/recordings/hard_2_1_{str(each["id"])}/{dateStr}T{hour}/ | grep "2_1_{str(each["id"])}_{dateStr}T{hour}_{minute}" | wc -l'
            
            output = subprocess.check_output(finalAddress, shell=True)
            output = output.decode().strip()
            count = int(output)
            
            curr["Camid"] = each["id"]
            curr["hard_frame_count"] = count
            result.append(curr)
        
        return result
        
    def get_system_info(self):
        cpu_usage = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        mem_usage = mem.percent

        cpu_model = platform.processor()

        gpu_total_memory = psutil.virtual_memory().total / (1024**3)
    
        if platform.system() == 'Linux':
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.strip() and line.rstrip('\n').startswith('model name'):
                            cpu_model = line.rstrip('\n').split(':')[1].strip()
                            break

                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.strip() and line.rstrip('\n').startswith('MemTotal'):
                            mem_total_kb = int(line.rstrip('\n').split(':')[1].strip().split()[0])
                            mem_total_gb = mem_total_kb // (1024 ** 2)
                            break

            except FileNotFoundError:
                pass
        system_info = {
            'CPUUsage%': cpu_usage,
            'MemoryUsage%': mem_usage,
            'CPUModelName': cpu_model,
            'TotalMemoryinGB': gpu_total_memory
        }
        
        return system_info

    
    def combined_array(self):
        
        total_cameras_data = self.total_camera()
        frame_count_data = self.frame_count()
        Intended_fps_data = self.Intended_Fps()
        number_of_checkpoints_data = self.number_of_checkpoints()
        hard_frame_count = self.hard_frame_count()
        system_info = self.get_system_info()

        for each in total_cameras_data:
            curr = {
                "Camid":each["id"],
                "CamNam":each["CamName"],
                "FrameCount":0
                }
            for fc in frame_count_data:
                if curr["Camid"] == fc["CamID_id"]:
                    curr["FrameCount"] = fc["frame_count"]
                    break
            for ifps in Intended_fps_data:
                s = ifps["advanced_setting_value"]
                json_acceptable_string = s.replace("'", "\"")
                d = json.loads(json_acceptable_string)
                if curr["Camid"] == ifps["id"]:
                    curr["IntendedFps"] = d["value"]
                    break
                else:
                    curr["IntendedFps"] = 0
            for hfc in hard_frame_count:
                if curr["Camid"] == hfc["Camid"]:
                    curr["Hardframecount"] = hfc["hard_frame_count"]
            self.res.append(curr)
        
        for curr in self.res:
            flag = False
            
            for cp in number_of_checkpoints_data:
                if curr["Camid"] == cp["CamID_id"]:
                    flag = True
                    dummy = dict()
                    curr["CheckpointType"] = cp["MarkingGeometry__0__checkpointType"]
                    curr["NumberOfCheckpoints"] = cp["NumberOfCheckpoints"]
                    for each in curr:
                        dummy[each] = curr[each]
                    self.result.append(dummy)
            if flag == False:
                curr["CheckpointType"] = "Not Active"
                curr["NumberOfCheckpoints"] = 0
                dummy = dict()
                for each in curr:
                    dummy[each] = curr[each]
                self.result.append(dummy)
                        
        
        self.result.append(system_info)
        
        return self.result

    def dataToCSV(self):
        dataSet = self.combined_array()
        df = pd.DataFrame(dataSet) 
        df.to_csv(self.path + "/csv.csv", index=False)
        

if __name__=='__main__':
    last = datetime.now()
    main = Main()
    main.dataToCSV()
    print("Completed")
    print("Time of execution -->",datetime.now()-last)
    

