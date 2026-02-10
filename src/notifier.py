import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class Notifier:
    """多渠道通知"""
    
    def __init__(self, config):
        self.config = config
        self.notification_config = config['notification']
        self.logger = logging.getLogger(__name__)
    
    def send(self, subject: str, content: str):
        """发送通知"""
        if not self.notification_config['enabled']:
            self.logger.info("通知功能已禁用")
            return
        
        methods = self.notification_config['methods']
        
        if 'email' in methods:
            self._send_email(subject, content)
        
        if 'wecom' in methods and self.notification_config.get('wecom', {}).get('enabled'):
            self._send_wecom(content)
    
    def _send_email(self, subject: str, content: str):
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
                <pre style="background-color: #f5f5f5; padding: 15px; border-radius: 5px;">
{content}
                </pre>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
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