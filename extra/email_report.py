import os
import glob
import sys
import traceback
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import cv2

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from datetime import date, datetime, timedelta

# Logging into Uwsgi.log as we are using Djnago here
# TODO: Logging sh0uld be shifted to reports.log
import logging
logger = logging.getLogger(__name__)

from camera.models import Camera, Camframelog, Cameventlog, Alert, Survfeatconfig, Maintenance

from django.db.models.functions import TruncHour
from django.db.models import Count

import json
import pandas
import socket

from root_config import EMAIL_TO_DICT, EMAIL_TO, send_from_messaging
from .models import Projects
from camera.system_check import SystemCheck
from camera.send_emails_to_messaging import send_to_messaging
from organization.models import Organization

class EmailReport:
    def __init__(self, mail_type=None):
        self.mail_type = mail_type
        if self.mail_type == 'hourly':
            self.today = datetime.now()
            self.yesterday = self.today - timedelta(days=1)
        else:
            self.today = date.today()
            self.yesterday = self.today - timedelta(days=1)

        self.report_json = dict()
        self.report_json_status = dict()
        self.report_json_framecount = dict()

        self.for_csv = dict()

        self.SENDER_EMAIL = 'support@paralaxiom.com'
        self.SENDER_PASSWORD = 'P@ralaxiom1' # Hardcoding this as config email parameters would be deleted

        self.email = EMAIL_TO_DICT

        self.csv_path = '/opt/paralaxiom/vast/reports_temp/'
        self.status_image_path = '/opt/paralaxiom/vast/email_screenshots/'
        if not os.path.exists(self.csv_path):
            os.makedirs(self.csv_path)

    def to_csv(self):
        pass

    def check_camera_health(self, frame_count, OrgID, OrgName):
        all_cams = Camera.objects.filter(OrgID=OrgID)
        parsed = {}
        cam_details = []

        frame_count.drop(frame_count.columns[[0, 2, 3]], axis=1, inplace=True)
        parsed = json.loads(frame_count.to_json(orient="split"))

        for row in parsed["data"]:
            avg = sum(row[2:])/len(row[2:])

            if row[1]<avg:
                for cam in all_cams:
                    if cam.CamName == row[0]:
                        x = Projects.objects.filter(OrgID=OrgID, id=cam.ProjectID_id, Active=True).values()[0]
                        camId = cam.id
                cam_details.append({"org_name":OrgName,"project_name":x["ProjectName"],"camId":camId,"cam_name":row[0],"latest_frame_count":row[1],"avg":round(avg,2)})

        return cam_details

    def send_camera_health_email(self, frame_count, time_diff, OrgID, OrgName:str, a=True):
        cam_details = self.check_camera_health(frame_count, OrgID, OrgName)
        camera_health_info = """<tr>
                                    <th>Organization</th>
                                    <th>Project</th>
                                    <th>Camera ID</th>
                                    <th>Camera Name</th>
                                    <th>Latest Frame Count</th>
                                    <th>Average</th>
                                </tr>"""
        if len(cam_details) != 0:
            for cam in cam_details:
                camera_health_info += """<tr>
                                            <td>"""+str(cam["org_name"])+"""</td>
                                            <td>"""+str(cam["project_name"])+"""</td>
                                            <td>"""+str(cam["camId"])+"""</td>
                                            <td>"""+str(cam["cam_name"])+"""</td>
                                            <td>"""+str(cam["latest_frame_count"])+"""</td>
                                            <td>"""+str(cam["avg"])+"""</td>
                                        </tr>"""

            try:
                s = smtplib.SMTP(host='smtp.zoho.com', port=587)
                s.starttls()
            except Exception as err:
                err_traceback = traceback.format_exc()
                logger.error(f'{err}\n{err_traceback}')
                return

            try:
                s.login(self.SENDER_EMAIL, self.SENDER_PASSWORD)
            except smtplib.SMTPAuthenticationError:
                print("Authentication Error. Please Check your Email and Password.")
                logger.error("Authentication Error. Please Check your Email and Password.")

            try:
                email_to = self.email[OrgName]
            except KeyError:
                print(f'The Organization : {OrgName}\'s emails are not configured. Sending te maintenance mails to {EMAIL_TO}.')
                email_to = EMAIL_TO

            for i in range(len(email_to)):
                msg = MIMEMultipart()
                msg['From'] = self.SENDER_EMAIL
                msg['Subject'] = f"\U0001F534 Camera Health Info for {socket.gethostname()}"

                message = """\
                            <html>
                                <head>
                                    <style>
                                        table {
                                            font-family: Arial, Helvetica, sans-serif;
                                            border-collapse: collapse;
                                            width: 100%;
                                        }

                                        table td, table th {
                                            border: 1px solid #ddd;
                                            padding: 8px;
                                            text-align: left;
                                        }

                                        table tr:nth-child(even){background-color: #f2f2f2;}

                                        table tr:hover {background-color: #ddd;}
                                    </style>
                                </head>
                                <body>
                                    <div>
                                        Hi<br>
                                        This is a camera health info email from Paralaxiom.<br>
                                        This is generated from """+str(socket.gethostname())+""".<br>
                                        Last frame count for the following cameras was found to be less than average of other frame counts.<br><br>
                                        <table>"""+camera_health_info+"""</table><br>
                                        Thank you
                                    </div>
                                </body>
                            </html>
                        """

                msg['To'] = email_to[i] 
                msg.attach(MIMEText(message, 'html'))

                try:
                    s.send_message(msg)
                    response = s.noop()
                    print(f"Message Sent for {email_to[i]}")
                    print("----------------")
                    print(response)
                    logger.info(f"Message Sent for {email_to[i]}\n{response}")
                except Exception as err:
                    print(err)
                    logger.error(err)
            s.quit()
        


    def send_email(self, files_to_send, time_diff, OrgName:str, a=True):

        try:
            s = smtplib.SMTP(host='smtp.zoho.com', port=587)
            s.starttls()
        except Exception as err:
            err_traceback = traceback.format_exc()
            logger.error(f'{err}\n{err_traceback}')
            return

        try:
            s.login(self.SENDER_EMAIL, self.SENDER_PASSWORD)
        except smtplib.SMTPAuthenticationError:
            print("Authentication Error. Please Check your Email and Password.")
            logger.error("Authentication Error. Please Check your Email and Password.")

        try:
            # email_to = self.email[OrgName]
            email_to = ["chaitanyatyagi1540@gmail.com"]
        except KeyError:
            print(f'The Organization : {OrgName}\'s emails are not configured. Sending te maintenance mails to {EMAIL_TO}.')
            email_to = EMAIL_TO

        for i in range(len(email_to)):

            msg = MIMEMultipart()
            msg['From'] = self.SENDER_EMAIL
            if not time_diff:
                msg['Subject'] = f"Maintenance Email for {socket.gethostname()}"
            else:
                msg['Subject'] = f"\U0001F534 Maintenance Email for {socket.gethostname()}"

            if a:
                for path in files_to_send:
                    file_name = path.split('/')[-1]
                    attachment = open(path, "rb")

                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', "attachment", filename=file_name)

                    msg.attach(part)
            if time_diff:
                message = f"""
                Hi,
                This is a maintenance message from Paralaxiom for {OrgName}.
                Last frame came {time_diff} seconds ago.
                This is generated from {socket.gethostname()}. 
                Thank you
                """
            else:
                message = f"""
                Hi,
                This is a maintenance message from Paralaxiom for {OrgName}.
                This is generated from {socket.gethostname()}. 
                Thank you
                """

            msg['To'] = email_to[i] # organization name will need to send
            msg.attach(MIMEText(message, 'plain'))

            try:
                s.send_message(msg)
                response = s.noop()
                print(f"Message Sent for {email_to[i]}")
                print("----------------")
                print(response)
                logger.info(f"Message Sent for {email_to[i]}\n{response}")
            except Exception as err:
                print(err)
                logger.error(err)
        s.quit()

    def daily_report(self, all_cams, OrgID):

        report_count = dict()
        for cam in all_cams:
            report_count[cam.id] = {}
            frames = Camframelog.objects.filter(CamID=cam, FrameTime__gt=self.yesterday,
                                                FrameTime__lt=self.today).count()
            events = Cameventlog.objects.filter(CamID=cam, EventTime__gt=self.yesterday,
                                                EventTime__lt=self.today).count()
            alerts = Alert.objects.filter(CamID=cam, EventTime__gt=self.yesterday, EventTime__lt=self.today).count()

            report_count[cam.id]["cam_name"] = cam.CamName
            report_count[cam.id]["camera_active_yn"] = cam.Active
            report_count[cam.id]["ai_model_enabled"] = cam.AIModelEnabled
            report_count[cam.id]["frames"] = frames
            report_count[cam.id]["events"] = events
            report_count[cam.id]["alerts"] = alerts

        add_del_cams = Camera.objects.filter(CreationDate__gt=self.yesterday,
                                             CreationDate__lt=self.today, 
                                             OrgID=OrgID).values("Active").annotate(total=Count("id"))
        checkpoints = Survfeatconfig.objects.filter(CreationDate__gt=self.yesterday,
                                                    CreationDate__lt=self.today, 
                                                    OrgID=OrgID).all()
        inactive_checkpoints = 0
        active_checkpoints = 0
        for i in checkpoints:
            if i.Active == False:
                inactive_checkpoints += 1
            else:
                active_checkpoints += 1
        report_count["added_deleted_camera"] = {}
        report_count["added_deleted_checkpoints"] = {}
        for cam_sts in add_del_cams:
            if cam_sts["Active"]:
                report_count["added_deleted_camera"]["added_cam"] = cam_sts["total"]
            else:
                report_count["added_deleted_camera"]["deleted_cam"] = cam_sts["total"]

        if not report_count["added_deleted_camera"]:
            report_count["added_deleted_camera"]["added_cam"] = 0
            report_count["added_deleted_camera"]["deleted_cam"] = 0

        for checkpoint in checkpoints:
            if checkpoint.Active:
                report_count["added_deleted_checkpoints"]["new_checkpoints"] = active_checkpoints
            else:
                report_count["added_deleted_checkpoints"]["delete_checkpoints"] = inactive_checkpoints
            # if checkpoint["Active"]:
            #     report_count["added_deleted_checkpoints"]["new_checkpoints"] = checkpoint["total"]
            # else:
            #     report_count["added_deleted_checkpoints"]['delete_checkpoint'] = checkpoint["total"]

        if not report_count["added_deleted_checkpoints"]:
            report_count["added_deleted_checkpoints"]["new_checkpoints"] = 0
            report_count["added_deleted_checkpoints"]['delete_checkpoint'] = 0

        return report_count

    def services_status_in_timestamp(self):
        services_status = Maintenance.objects.filter(CreationDate__gt=self.yesterday,
                                                     CreationDate__lt=self.today,
                                                     Source='system_check').values("CreationDate",
                                                                                   "SystemHealth").order_by('CreationDate')
        services_health_json = dict()
        for services in services_status:
            str_hour_time = services['CreationDate'].strftime("%Y-%m-%d, %H:%M:%S")
            services_health_json[str_hour_time] = {}
            for key in services["SystemHealth"]["Service Status"]:
                services_health_json[str_hour_time][key] = services["SystemHealth"]["Service Status"][key]

        return services_health_json

    def run(self, OrgID):
        all_cams = Camera.objects.filter(OrgID=OrgID)# add organaization filter here
        if not os.path.exists(self.csv_path +OrgID.OrgName):
            os.makedirs(self.csv_path +OrgID.OrgName)

        if not os.path.exists(self.status_image_path +OrgID.OrgName):
            os.makedirs(self.status_image_path +OrgID.OrgName)
        # clean for csv and other jsons and dicts
        self.for_csv = {}
        self.report_json = {}
        self.report_json_framecount = {}
        self.report_json_status = {}
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
            frame_count = Camframelog.objects.filter(CamID=cam, FrameTime__gt=self.yesterday,
                                                     FrameTime__lt=self.today).annotate(
                hour=TruncHour('FrameTime')).values('hour').annotate(frames=Count('id')).order_by('hour')
            
            if self.mail_type == 'hourly':
                start_time = self.yesterday.replace(microsecond=0, second=0, minute=0)    # replace will round off minutes and seconds to 00
                end_time = self.today 
            else:
                start_time = datetime.combine(self.yesterday, datetime.min.time())
                end_time = datetime.combine(self.today, datetime.min.time())


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

            # for hr in frame_count:
                
            #     str_hour_time = hr['hour'].strftime("%Y-%m-%d, %H:%M:%S")
            #     self.report_json[cam.CamName]['frame_count'][str_hour_time] = hr['frames']
            #     self.report_json_framecount[cam.CamName][str_hour_time] = hr['frames']

            #     try:
            #         self.for_csv[str_hour_time][cam.CamName] = hr['frames']
            #     except KeyError:
            #         self.for_csv[str_hour_time] = {}
            #         self.for_csv[str_hour_time][cam.CamName] = hr['frames']

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

        
        df = pandas.read_json(json.dumps(dict(sorted(self.for_csv.items()))))
        cols_as_date = df.columns
        df = df[sorted(cols_as_date,reverse=True)]
        frame_count = df
        df.to_csv(self.csv_path + OrgID.OrgName + '/frame_count.csv', index_label="camera_id")

        reports_count = self.daily_report(all_cams, OrgID=OrgID)
        df = pandas.DataFrame(reports_count).T
        df.to_csv(self.csv_path+ OrgID.OrgName + '/reports_count.csv', index_label='camera_id')
        # pandas.read_json(json.dumps(reports_count)).to_csv(self.csv_path + 'reports_count.csv')

        system_health = SystemCheck(OrgId=OrgID) 
        system_health_json, time_diff = system_health.run()
        self.system_data_json = system_health_json
        self.graph(OrgID.OrgName)
        system_health_json = json.dumps(system_health_json)

        pandas.read_json(system_health_json).to_csv(self.csv_path + OrgID.OrgName + '/system_health.csv',index_label='Specification')
        service_status = self.services_status_in_timestamp()
        df = pandas.read_json(json.dumps(service_status))
        cols_as_date = df.columns
        df = df[sorted(cols_as_date,reverse=True)]
        df.to_csv(self.csv_path + OrgID.OrgName + '/services_health.csv')

        writer = pandas.ExcelWriter(
            self.csv_path + OrgID.OrgName + '/reports_' + self.yesterday.strftime("%Y-%m-%d") + '.xlsx',
            engine="xlsxwriter")
        for f in glob.glob(os.path.join(self.csv_path + OrgID.OrgName , "*.csv")):
            df = pandas.read_csv(f)
            df = df.reset_index(drop=True)
            df.index += 1
            df.to_excel(writer, sheet_name=os.path.basename(f)[:31], index=True)

        writer.save()

        sheet_path = self.csv_path + OrgID.OrgName + '/reports_' + self.yesterday.strftime("%Y-%m-%d") + '.xlsx'
        files_to_send = [sheet_path,self.system_status_path,self.service_status_path]

        if send_from_messaging:
            # Sending through messaging server
            send_to_messaging(files_to_send, 'reports_' + self.yesterday.strftime("%Y-%m-%d") + '.xlsx', time_diff, OrgID.OrgName, True)
        else:
            self.send_email(files_to_send, time_diff, OrgID.OrgName, True)
            self.send_camera_health_email(frame_count   , time_diff, OrgID.id, OrgID.OrgName, True)        
        
        return True

    def graph(self, org_name):

        cpu = (self.system_data_json['CPU'])['CPU Load']
        disk = self.system_data_json['Disk Usage']
        ram = self.system_data_json['Ram Usage']
        swap = self.system_data_json['Swap Space']
        total_ram = int(ram['Used Ram'][:-3])+int(ram['Free Ram'][:-3])+int(ram['Available Ram'][:-3])
        used_ram = (int(ram['Used Ram'][:-3])*100)/total_ram
        swap_usage = swap['Swap Space Percentage']
        total_disk_space =int(disk['Used Space Storage'][:-3])+int(disk['Free Space Storage'][:-3])
        used_disk = (int(disk['Used Space Storage'][:-3])*100)/total_disk_space
        plotdata = pd.DataFrame({
            "used":[int(ram['Used Ram'][:-3]),84,int(disk['Used Space Storage'][:-3]),int(float(swap['Swap Space Percentage'][:-1]))],
            "free":[int(ram['Free Ram'][:-3]),0,0,0],
            "available":[int(ram['Available Ram'][:-3]),15,int(disk['Free Space Storage'][:-3]),(100 - int(float(swap['Swap Space Percentage'][:-1]))) ]},
            # index =["RAM","CPU","DISK","SWAP SPACE"])
            index =["RAM","CPU","DISK"])
        
        y = ["USED","FREE","AVAILABLE"]
        colors = plt.get_cmap('Blues')(np.linspace(0.2, 0.7, 4))
        explode = (0.1,0.1,0.1)
        # fig, axs = plt.subplots(1, 4,figsize=(15,5))
        # cnt = 0
        for each in plotdata.index:
            x = [plotdata.loc[each]["used"],plotdata.loc[each]["free"],plotdata.loc[each]["available"]]
            # axs[cnt].pie(x, colors=colors,explode=explode,shadow=True,startangle=90,labels = y,autopct='%0.1f%%')
            # axs[cnt].set_title(f'{each} STORAGE STATS')
            # cnt += 1
            plt.pie(x, colors=colors,explode=explode,shadow=True,startangle=90,labels = y,autopct='%0.1f%%')
            if send_from_messaging:
                self.system_status_path = os.path.join(self.csv_path, org_name,f'{each}_status.png')
            else:
                self.system_status_path = os.path.join(self.status_image_path, org_name,f'{each}_status.png')
            plt.savefig(self.system_status_path)

        # if send_from_messaging:
        #     self.system_status_path = os.path.join(self.csv_path, org_name,'system_status.png')
        # else:
        #     self.system_status_path = os.path.join(self.status_image_path, org_name,'system_status.png')
        # plt.savefig(self.system_status_path)

        if send_from_messaging:
            self.service_status_path = os.path.join(self.csv_path , org_name,'service_status.jpg')
        else:
            self.service_status_path = os.path.join(self.status_image_path, org_name, 'service_status.jpg')

        im = Image.new('RGB',(250, 310), (255, 255, 255))

        im.save(self.service_status_path)
        img = cv2.imread(self.service_status_path)


        x = 25
        y = 50

        org = (x,y)



        for key in self.system_data_json['Service Status'] :
            if self.system_data_json['Service Status'][key] == "Active" :
                status_color = (0,128,0)
            else :
                status_color = (0, 0, 255)

            org = (x, y)
            center_coordinates = (x+180, y-7)
            image = cv2.putText(img,key, org, cv2.FONT_HERSHEY_SIMPLEX,0.75, (0, 0, 0), 1, cv2.LINE_AA)
            image = cv2.circle(image, center_coordinates, 10, status_color, -1)
            y = y+40

        cv2.imwrite(self.service_status_path, image)


if __name__ == '__main__':
    args = sys.argv
    print(args, len(args))
    mail_type = None
    try:
        mail_type = args[1]
    except IndexError:
        mail_type = None
    er = EmailReport(mail_type)
    # disk_space_email = DiskSpaceWarningEmail()
    try:
        orgs = Organization.objects.exclude(OrgName='')
        for OrgID in orgs:
            report_json = er.run(OrgID)
        # send_disk_mail = disk_space_email.run()
    except Exception as e:
        err_trace = traceback.format_exc()
        logger.error(f'{e}\n{err_trace}')
        print(f'{e}\n{err_trace}')



# if __name__ == '__main__':
#     args = sys.argv
#     print(args, len(args))
#     mail_type = None
#     try:
#         mail_type = args[1]
#     except IndexError:
#         mail_type = None
#     er = EmailReport(mail_type)
#     try:
#         report_json = er.run()
#     except Exception as e:
#         err_trace = traceback.format_exc()
#         logger.error(f'{e}\n{err_trace}')
#         print(f'{e}\n{err_trace}')

# color = ['#fc5c65','#fed330','#26de81']
        # plotdata.apply(lambda x:x/x.sum(), axis=1).plot(kind='barh',color = color, stacked=True, legend=False,figsize=(14, 5))
        # plt.text(0.01,2.95,f'swap used {swap_usage}')
        # plt.text(0.01,1.95,f'storage used Storage {round(used_disk,2)}%')
        # plt.text(0.01,0.95,f'cpu used {cpu}')
        # plt.text(0.01,-0.05,f'ram used {round(used_ram,2)}%')