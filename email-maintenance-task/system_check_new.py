import os
import django
import pandas as pd
import json
import matplotlib.pyplot as plt
from PIL import Image
import cv2
import seaborn as sb
from datetime import date,datetime,timedelta,time
from camera.models import Camera, Camframelog, Cameventlog, Alert, Survfeatconfig, Maintenance
from .models import Projects
from django.db.models import Count
from camera.send_emails_to_messaging import send_to_messaging
from camera.system_check import SystemCheck
from django.db.models.functions import TruncHour
from collections import defaultdict
from django.db.models import Count



os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

class SystemCheckNew(SystemCheck):

    def get_cpu_usage(self,data):
        return float(data["CPU Load"].split(" ")[0])

    def get_ram_usage(self,data):
        total,used = 0,0
        for key in data:
            if key == "Free Ram" or key == "Used Ram" or key == "Available Ram":
                total += int(data[key].split(" ")[0])
            if key == "Used Ram":
                used = int(data[key].split(" ")[0])
        return (used*100)/total
        
    def get_disk_usage(self,data):
        total,used = 0,0
        for key in data:
            if key == "Free Space Storage" or key == "Used Space Storage":
                total += int(data[key].split(" ")[0])
            if key == "Used Space Storage":
                used = int(data[key].split(" ")[0])
        return (used*100)/total

    def get_data_not_hourly(self,today,yesterday):
        maintenance_data = Maintenance.objects.filter(Source="system_check",CreationDate_lte=today, CreationDate_gt=yesterday)
        curr_stats = dict()
        system_stats = []
        for each in maintenance_data:
            add_status = dict()
            curr_stats["Date-Time"] = each.CreationDate.time()
            curr_stats["CPU USED STORAGE"] = self.get_cpu_usage(each.SystemHealth["CPU"])
            curr_stats["RAM USED STORAGE"] = self.get_ram_usage(each.SystemHealth["Ram Usage"])
            curr_stats["DISK USED STORAGE"] = self.get_disk_usage(each.SystemHealth["Disk Usage"])
            for key in curr_stats:
                add_status[key] = curr_stats[key]
            system_stats.append(add_status)
        return system_stats
    
    def get_data_hourly(self):
        system_stats = self.run()
        return system_stats
    
    
    def graph(self,org_name,csv_path,status_image_path,system_data_json,service_status_path,system_status_path,today,yesterday):

        system_stats = self.get_data_not_hourly(today,yesterday)
        plotData = pd.DataFrame(system_stats)
        cnt,first = 0,True
        for each in plotData:
            if first:
                first = False
                continue
            g2 = sb.lineplot(data=plotData,x=plotData["Date-Time"].astype(str),y=plotData[each])
            g2.set(xticklabels=[])  
            g2.tick_params(bottom=False) 
            if send_to_messaging:
                system_status_path.append(os.path.join(csv_path, org_name,f'{each} STATUS.png'))
            else:
                system_status_path.append(os.path.join(status_image_path, org_name,f'{each} STATUS.png'))
            plt.savefig(system_status_path[cnt])
            cnt += 1
            plt.clf()
        
        if send_to_messaging:
            service_status_path.append(os.path.join(csv_path , org_name,'service_status.jpg'))
        else:
            service_status_path.append(os.path.join(status_image_path, org_name, 'service_status.jpg'))

        im = Image.new('RGB',(250, 310), (255, 255, 255))

        im.save(service_status_path[0])
        img = cv2.imread(service_status_path[0])

        x = 25
        y = 50

        org = (x,y)

        for key in system_data_json['Service Status'] :
            if system_data_json['Service Status'][key] == "Active":
                status_color = (0,128,0)
            else :
                status_color = (0, 0, 255)
            org = (x, y)
            center_coordinates = (x+180, y-7)
            image = cv2.putText(img,key, org, cv2.FONT_HERSHEY_SIMPLEX,0.75, (0, 0, 0), 1, cv2.LINE_AA)
            image = cv2.circle(image, center_coordinates, 10, status_color, -1)
            y = y+40

        cv2.imwrite(service_status_path[0], image)


class CameraHealth:
    
    def check_camera_health(self, OrgID, frame_count_camera, OrgName):
        all_cams = Camera.objects.filter(OrgID=OrgID).select_related('ProjectID')
        parsed = frame_count_camera.drop(frame_count_camera.columns[[0, 2, 3]], axis=1).to_dict(orient='split')

        cam_details = []
        for row in parsed["data"]:
            cam_name = row[0]
            frame_counts = row[2:]

            avg_frame_count = sum(frame_counts) / len(frame_counts)

            if row[1] < avg_frame_count:
                cam = next((cam for cam in all_cams if cam.CamName == cam_name), None)
                if cam:
                    project = cam.ProjectID
                    cam_details.append({
                        "org_name": OrgName,
                        "project_name": project.ProjectName,
                        "camId": cam.id,
                        "cam_name": cam_name,
                        "latest_frame_count": row[1],
                        "avg": round(avg_frame_count, 2)
                    })

        return cam_details

class DailyReportDetails():

    
    def daily_report(self, yesterday, today, all_cams, OrgID):
        report_count = {}
        frames_counts = Camframelog.objects.filter(
            FrameTime__gt=yesterday,
            FrameTime__lt=today
        ).values('CamID').annotate(frames=Count('id'))

        events_counts = Cameventlog.objects.filter(
            EventTime__gt=yesterday,
            EventTime__lt=today
        ).values('CamID').annotate(events=Count('id'))

        alerts_counts = Alert.objects.filter(
            EventTime__gt=yesterday,
            EventTime__lt=today
        ).values('CamID').annotate(alerts=Count('id'))

        for cam in all_cams:
            cam_id = cam.id

            report_count[cam_id] = {
                "cam_name": cam.CamName,
                "camera_active_yn": cam.Active,
                "ai_model_enabled": cam.AIModelEnabled,
                "frames": next((frame['frames'] for frame in frames_counts if frame['CamID'] == cam_id), 0),
                "events": next((event['events'] for event in events_counts if event['CamID'] == cam_id), 0),
                "alerts": next((alert['alerts'] for alert in alerts_counts if alert['CamID'] == cam_id), 0)
            }

        add_del_cams = Camera.objects.filter(
            CreationDate__gt=yesterday,
            CreationDate__lt=today,
            OrgID=OrgID
        ).values('Active').annotate(total=Count('id'))

        report_count["added_deleted_camera"] = {
            "added_cam": next((cam_sts["total"] for cam_sts in add_del_cams if cam_sts["Active"]), 0),
            "deleted_cam": next((cam_sts["total"] for cam_sts in add_del_cams if not cam_sts["Active"]), 0)
        }

        checkpoints = Survfeatconfig.objects.filter(
            CreationDate__gt=yesterday,
            CreationDate__lt=today,
            OrgID=OrgID
        ).values('Active')

        inactive_checkpoints = checkpoints.filter(Active=False).count()
        active_checkpoints = checkpoints.filter(Active=True).count()

        report_count["added_deleted_checkpoints"] = {
            "new_checkpoints": active_checkpoints,
            "delete_checkpoints": inactive_checkpoints
        }

        return report_count
    
    def services_status_in_timestamp(self, yesterday, today):
        services_status = Maintenance.objects.filter(
            CreationDate__gt=yesterday,
            CreationDate__lt=today,
            Source='system_check'
        ).values("CreationDate", "SystemHealth").order_by('CreationDate')

        services_health_json = {
            str(services['CreationDate'].strftime("%Y-%m-%d, %H:%M:%S")): {
                key: services["SystemHealth"]["Service Status"][key]
                for key in services["SystemHealth"]["Service Status"]
            }
            for services in services_status
        }

        return services_health_json

class ExcelData:

    def _init_(self):
        self.for_csv = {}
        self.report_json = {}
        self.report_json_framecount = {}
        self.report_json_status = {}

    def frames_count(self,all_cams,mail_type,yesterday,today):
        self.for_csv['cam_name'] = {}
        self.for_csv['ai_model'] = {}
        self.for_csv['camera_active_yn'] = {}
        for cam in all_cams:
            self.for_csv['cam_name'][cam.id] = cam.CamName
            self.for_csv['ai_model'][cam.id] = cam.AIModelEnabled
            self.for_csv['camera_active_yn'][cam.id] = cam.Active
            self.report_json[cam.id] = {}
            self.report_json[cam.id]['frame_count'] = {}
            self.report_json_framecount[cam.id] = {}
            frame_count = Camframelog.objects.filter(CamID=cam, FrameTime__gt=yesterday,
                                                     FrameTime__lt=today).annotate(
                hour=TruncHour('FrameTime')).values('hour').annotate(frames=Count('id')).order_by('hour')

            if mail_type == 'hourly':
                start_time = yesterday.replace(
                    microsecond=0, second=0, minute=0)
                end_time = today
            else:
                start_time = datetime.combine(
                    yesterday, datetime.min.time())
                end_time = datetime.combine(today, datetime.min.time())

            for hr in frame_count:
                while start_time < hr['hour']:
                    str_hour_time = start_time.strftime("%Y-%m-%d, %H:%M:%S")
                    self.report_json[cam.id]['frame_count'][str_hour_time] = 0
                    self.report_json_framecount[cam.id][str_hour_time] = 0
                    try:
                        self.for_csv[str_hour_time][cam.id] = 0
                    except KeyError:
                        self.for_csv[str_hour_time] = {}
                        self.for_csv[str_hour_time][cam.id] = 0
                    start_time = start_time + timedelta(hours=1)

                str_hour_time = hr['hour'].strftime("%Y-%m-%d, %H:%M:%S")
                self.report_json[cam.id]['frame_count'][str_hour_time] = hr['frames']
                self.report_json_framecount[cam.id][str_hour_time] = hr['frames']
                try:
                    self.for_csv[str_hour_time][cam.id] = hr['frames']
                except KeyError:
                    self.for_csv[str_hour_time] = {}
                    self.for_csv[str_hour_time][cam.id] = hr['frames']
                start_time = start_time + timedelta(hours=1)
            while start_time <= end_time:
                str_hour_time = start_time.strftime("%Y-%m-%d, %H:%M:%S")
                self.report_json[cam.id]['frame_count'][str_hour_time] = 0
                self.report_json_framecount[cam.id][str_hour_time] = 0
                try:
                    self.for_csv[str_hour_time][cam.id] = 0
                except KeyError:
                    self.for_csv[str_hour_time] = {}
                    self.for_csv[str_hour_time][cam.id] = 0
                start_time = start_time + timedelta(hours=1)
            if len(frame_count) > 0:
                if cam.Active:
                    if cam.InService:
                        self.report_json[cam.id]['Active'] = True
                        self.report_json_status[cam.id] = True
                    else:
                        self.report_json[cam.id]['Active'] = False
                        self.report_json_status[cam.id] = False
                else:
                    self.report_json[cam.id]['Active'] = False
                    self.report_json_status[cam.id] = False
            else:
                if cam.Active:
                    self.report_json[cam.id]['Active'] = False
                    self.report_json_status[cam.id] = False
                else:
                    self.report_json.pop(cam.id, None)
                    self.report_json_framecount.pop(cam.id, None)
                    self.report_json_status.pop(cam.id, None)
            
        return self.for_csv