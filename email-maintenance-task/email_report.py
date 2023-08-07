from camera.system_check_new import SystemCheckNew, CameraHealth, DailyReportDetails, ExcelData
from organization.models import Organization
from camera.send_emails_to_messaging import send_to_messaging
from camera.system_check import SystemCheck
from root_config import EMAIL_TO_DICT, EMAIL_TO, send_from_messaging
import socket
import pandas
import json
from camera.models import Camera
import logging
from datetime import date, datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import smtplib
import os
import glob
import sys
import traceback
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()
logger = logging.getLogger(_name_)

class EmailReport():

    def _init_(self, mail_type=None):
        self.mail_type = mail_type
        if self.mail_type == 'hourly':
            self.today = datetime.now()
            self.yesterday = self.today - timedelta(days=1)
        else:
            self.today = datetime(2023,6,2,0,0,0)
            # self.today = date.today()
            self.yesterday = self.today - timedelta(days=1)
        self.for_csv = dict()
        self.SENDER_EMAIL = 'support@paralaxiom.com'
        self.SENDER_PASSWORD = 'P@ralaxiom1'   
        self.email = EMAIL_TO_DICT
        self.service_status_path = []
        self.system_status_path = []
        self.csv_path = '/opt/paralaxiom/vast/reports_temp/'
        self.status_image_path = '/opt/paralaxiom/vast/email_screenshots/'
        if not os.path.exists(self.csv_path):
            os.makedirs(self.csv_path)

    def send_camera_health_email(self,frame_count_camera, OrgID, OrgName: str, a=True):
        system = CameraHealth()
        cam_details = system.check_camera_health( OrgID,frame_count_camera, OrgName)
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
                # return

            try:
                s.login(self.SENDER_EMAIL, self.SENDER_PASSWORD)
            except smtplib.SMTPAuthenticationError:
                print("Authentication Error. Please Check your Email and Password.")
                logger.error(
                    "Authentication Error. Please Check your Email and Password.")

            try:
                # email_to = self.email[OrgName]
                email_to = ["chaitanyatyagi1540@gmail.com","Sai.kumar@paralaxiom.com"]
            except KeyError:
                print(
                    f'The Organization : {OrgName}\'s emails are not configured. Sending te maintenance mails to {EMAIL_TO}.')
                # email_to = EMAIL_TO
                email_to = ["chaitanyatyagi1540@gmail.com","Sai.kumar@paralaxiom.com"] 
            
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

    def create_email_message(self, OrgName, time_diff, files_to_send, cpu, ram, disk):
        css_style = """
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.5;
                }

                .container {
                    max-width: 1000px;
                    margin: 0 auto;
                    padding: 20px;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    background-color: #f5f5f5;
                }

                .header {
                    text-align: center;
                    margin-bottom: 20px;
                }

                .main-body {
                    margin-bottom: 20px;
                }

                .image-container {
                    margin-top: 20px;
                    text-align: center;
                }

                .image-container img {
                    max-width: 100%;
                    height: auto;
                    display: block;
                    margin: 10px auto;
                }

                .regards {
                    text-align: left;
                    margin-top: 20px;
                    font-weight: bold;
                }
            </style>
        """

        if self.mail_type != "hourly":
            img_display = """
                <div class="image-container">
                    <div><strong>CPU Used Storage Percentage Graph</strong></div>
                    <img src="cid:image1" alt="CPU Graph">
                    <div><strong>RAM Used Storage Percentage Graph</strong></div>
                    <img src="cid:image2" alt="RAM Graph">
                    <div><strong>DISK Used Storage Percentage Graph</strong></div>
                    <img src="cid:image3" alt="DISK Graph">
                </div>
            """
            img_not_display = ""
            message = f"""
            <html>
                <head>
                    {css_style}
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h3>Greetings from Team Paralaxiom</h3>
                        </div>
                        <div class="main-body">
                            <p>This is a maintenance message from Paralaxiom for <strong>{OrgName}</strong>.</p>
                            <p>This is generated from <strong>{socket.gethostname()}</strong>.</p>
                            <p>Last frame came <strong>{time_diff}</strong> seconds ago.</p>
                        </div>
                        {img_display if len(files_to_send) > 2 else img_not_display}
                        <div class="regards">
                            <p>Regards,</p>
                            <p><strong>Team Paralaxiom</strong></p>
                        </div>
                    </div>
                </body>
            </html>
            """
        else:
            message = f"""
            <html>
                <head>
                    {css_style}
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h3>Greetings from Team Paralaxiom</h3>
                        </div>
                        <div class="main-body">
                            <p>This is a maintenance message from Paralaxiom for <strong>{OrgName}</strong>.</p>
                            <p>This is generated from <strong>{socket.gethostname()}</strong>.</p>
                            <p>Last frame came <strong>{time_diff}</strong> seconds ago.</p>
                            <p>CPU Used Storage Percentage: {cpu}</p>
                            <p>RAM Used Storage Percentage: {ram}%</p>
                            <p>DISK Used Storage Percentage: {disk}%</p>
                        </div>
                        <div class="regards">
                            <p>Regards,</p>
                            <p><strong>Team Paralaxiom</strong></p>
                        </div>
                    </div>
                </body>
            </html>
            """
        return message



    def send_email(self, files_to_send, time_diff, OrgName: str, a=True):
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
            logger.error(
                "Authentication Error. Please Check your Email and Password.")

        try:
            email_to = ["chaitanyatyagi1540@gmail.com"]   # email_to = self.email[OrgName]
        except KeyError:
            print(
                f'The Organization : {OrgName}\'s emails are not configured. Sending te maintenance mails to {EMAIL_TO}.')
            # email_to = EMAIL_TO
            email_to = ["chaitanyatyagi1540@gmail.com","Sai.kumar@paralaxiom.com"] 

        for i in range(len(email_to)):

            msg = MIMEMultipart()
            msg['From'] = self.SENDER_EMAIL
            if not time_diff:
                msg['Subject'] = f"Maintenance Email for {socket.gethostname()}"
            else:
                msg['Subject'] = f"\U0001F534 Maintenance Email for {socket.gethostname()}"

            if a:
                cnt = 0
                for path in files_to_send:
                    if cnt == 2:
                        break
                    file_name = path.split('/')[-1]
                    attachment = open(path, "rb")
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition',
                                    "attachment", filename=file_name)
                    cnt += 1

                    msg.attach(part)
            
            system_health = SystemCheck()
            system_health_json, time_diff = system_health.run()
            cpu = system_health_json['CPU']['CPU Load']
            ram = round((int(system_health_json['Ram Usage']['Used Ram'][:-3])*100)/(int(system_health_json['Ram Usage']['Used Ram'][:-3])+int(system_health_json['Ram Usage']['Free Ram'][:-3])+int(system_health_json['Ram Usage']['Available Ram'][:-3])),1)
            disk = round((int(system_health_json['Disk Usage']['Used Space Storage'][:-3])*100)/(int(system_health_json['Disk Usage']['Used Space Storage'][:-3])+int(system_health_json['Disk Usage']['Free Space Storage'][:-3])),1)
            
            
            if self.mail_type != "hourly" and len(files_to_send)>2:
                image_path1 = files_to_send[2]  
                with open(image_path1, 'rb') as image_file:
                    image_data1 = image_file.read()
            
                image_path2 = files_to_send[3] 
                with open(image_path2, 'rb') as image_file:
                    image_data2 = image_file.read()
            
                image_path3 = files_to_send[4] 
                with open(image_path3, 'rb') as image_file:
                    image_data3 = image_file.read()
            message = self.create_email_message(OrgName, time_diff, files_to_send, cpu, ram, disk)
            
            msg['To'] = email_to[i]  
            msg.attach(MIMEText(message, 'html'))

            if self.mail_type != "hourly" and len(files_to_send)>2:
                image_mime1 = MIMEImage(image_data1)
                image_mime1.add_header('Content-ID', '<image1>')
                msg.attach(image_mime1)

                image_mime2 = MIMEImage(image_data2)
                image_mime2.add_header('Content-ID', '<image2>')
                msg.attach(image_mime2)

                image_mime3 = MIMEImage(image_data3)
                image_mime3.add_header('Content-ID', '<image3>')
                msg.attach(image_mime3)

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

    def run(self, OrgID):
        
        all_cams = Camera.objects.filter(OrgID=OrgID)
        if not os.path.exists(self.csv_path + OrgID.OrgName):
            os.makedirs(self.csv_path + OrgID.OrgName)
        if not os.path.exists(self.status_image_path + OrgID.OrgName):
            os.makedirs(self.status_image_path + OrgID.OrgName)
        
        # -----------------------------------Frames Count Excel--------------------------------------
        excel_data = ExcelData()
        frame_count = excel_data.frames_count(all_cams,self.mail_type,self.yesterday,self.today)
        df = pandas.read_json(json.dumps(dict(sorted(frame_count.items()))))
        cols_as_date = df.columns
        df = df[sorted(cols_as_date, reverse=True)]
        frame_count_camera = df
        df.to_csv(self.csv_path + OrgID.OrgName +
                  '/frame_count.csv', index_label="camera_id")
        
        # -----------------------------------Reports Count Excel--------------------------------------
        daily_report = DailyReportDetails()
        reports_count = daily_report.daily_report(self.yesterday,self.today,all_cams,OrgID)
        df = pandas.DataFrame(reports_count).T
        df.to_csv(self.csv_path + OrgID.OrgName +
                  '/reports_count.csv', index_label='camera_id')

        # -----------------------------------System health Excel--------------------------------------
        system_health = SystemCheck(OrgId=OrgID)
        system_health_json, time_diff = system_health.run()
        self.system_data_json = system_health_json
        system_health_json = json.dumps(system_health_json)
        pandas.read_json(system_health_json).to_csv(
            self.csv_path + OrgID.OrgName + '/system_health.csv', index_label='Specification')
        
        # -----------------------------------Services health Excel--------------------------------------
        service_status = daily_report.services_status_in_timestamp(self.yesterday,self.today)
        df = pandas.read_json(json.dumps(service_status))
        cols_as_date = df.columns
        df = df[sorted(cols_as_date, reverse=True)]
        df.to_csv(self.csv_path + OrgID.OrgName + '/services_health.csv')

        # -----------------------------------System Stats graphs--------------------------------------
        system_check_new = SystemCheckNew()
        system_check_new.graph(OrgID.OrgName,self.csv_path,self.status_image_path,self.system_data_json,self.service_status_path,self.system_status_path,self.today,self.yesterday)

        writer = pandas.ExcelWriter(
            self.csv_path + OrgID.OrgName + '/reports_' +
            self.yesterday.strftime("%Y-%m-%d") + '.xlsx',
            engine="xlsxwriter")
        for f in glob.glob(os.path.join(self.csv_path + OrgID.OrgName, "*.csv")):
            df = pandas.read_csv(f)
            df = df.reset_index(drop=True)
            df.index += 1
            df.to_excel(writer, sheet_name=os.path.basename(f)
                        [:31], index=True)
        writer.save()

        sheet_path = self.csv_path + OrgID.OrgName + '/reports_' + \
            self.yesterday.strftime("%Y-%m-%d") + '.xlsx'
        files_to_send = [sheet_path, self.service_status_path[0]]

        if self.mail_type == "hourly":
            if send_from_messaging:
                send_to_messaging(files_to_send, 'reports_' + self.yesterday.strftime(
                    "%Y-%m-%d") + '.xlsx', time_diff, OrgID.OrgName, True)
            else:
                self.send_email(files_to_send, time_diff, OrgID.OrgName, True)
                self.send_camera_health_email(frame_count_camera, OrgID.id, OrgID.OrgName, True)
        else:
            for path in self.system_status_path:
                files_to_send.append(path)

            if send_from_messaging:
                send_to_messaging(files_to_send, 'reports_' + self.yesterday.strftime(
                    "%Y-%m-%d") + '.xlsx', time_diff, OrgID.OrgName, True)
            else:
                self.send_email(files_to_send, time_diff, OrgID.OrgName, True)
                self.send_camera_health_email(frame_count_camera, OrgID.id, OrgID.OrgName, True)

        return True

if _name_ == '_main_':
    args = sys.argv
    print(args, len(args))
    mail_type = None
    try:
        mail_type = args[1]
    except IndexError:
        mail_type = None
    er = EmailReport(mail_type)
    try:
        orgs = Organization.objects.exclude(OrgName='')
        for OrgID in orgs:
            report_json = er.run(OrgID)
    except Exception as e:
        err_trace = traceback.format_exc()
        logger.error(f'{e}\n{err_trace}')
        print(f'{e}\n{err_trace}')