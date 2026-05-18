import smtplib
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


class Notifier:
    """多渠道通知"""
    
    def __init__(self, config):
        self.config = config
        self.notification_config = config['notification']
        self.logger = logging.getLogger(__name__)
    
    def send(self, subject: str, content: str, attachments=None):
        """发送通知

        Args:
            subject: 邮件主题
            content: 邮件内容
            attachments: 附件列表（可选）
        """
        if not self.notification_config['enabled']:
            self.logger.info("通知功能已禁用")
            return

        methods = self.notification_config['methods']

        if 'email' in methods:
            self._send_email(subject, content, attachments)

        if 'wecom' in methods and self.notification_config.get('wecom', {}).get('enabled'):
            self._send_wecom(content)
    
    def _send_email(self, subject: str, content: str, attachments=None):
        """发送邮件"""
        try:
            email_config = self.notification_config['email']

            msg = MIMEMultipart()
            msg['From'] = email_config['sender']
            msg['To'] = ', '.join(email_config['receivers'])
            msg['Subject'] = subject

            # HTML格式
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                {content}
            </body>
            </html>
            """

            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            # 添加附件
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename="{os.path.basename(attachment_path)}"'
                            )
                            msg.attach(part)
                        self.logger.info(f"✓ 添加附件: {attachment_path}")
                    else:
                        self.logger.warning(f"附件不存在: {attachment_path}")

            # 发送
            with smtplib.SMTP_SSL(
                email_config['smtp_server'],
                email_config['smtp_port'], timeout=10) as server:
                server.login(email_config['sender'], email_config['password'])
                server.send_message(msg)

            self.logger.info(f"✓ 邮件已发送: {subject}")

        except Exception as e:
            self.logger.error(f"发送邮件失败: {e}")
    
    def _send_wecom(self, content: str):
        """发送企业微信通知"""
        try:
            import requests
            wecom_config = self.notification_config['wecom']
            
            data = {
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            
            response = requests.post(wecom_config['webhook_url'], json=data)
            
            if response.json().get('errcode') == 0:
                self.logger.info("✓ 企业微信通知已发送")
            else:
                self.logger.error(f"企业微信通知失败: {response.text}")
                
        except Exception as e:
            self.logger.error(f"发送企业微信通知失败: {e}")