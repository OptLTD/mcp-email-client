import os, smtplib, imaplib, email
from fastmcp import FastMCP
from typing import Dict, Any, List
from email.mime.text import MIMEText
from email.utils import formataddr
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

mcp = FastMCP("Email Client", version = "0.1.0")
class EmailClient:
    def __init__(self):
        self.username = os.environ.get("MAIL_USER_NAME", "")
        self.password = os.environ.get("MAIL_PASS_WORD", "")
        self.smtp_addr = os.environ.get("MAIL_SMTP_ADDR", "")
        self.imap_addr = os.environ.get("MAIL_IMAP_ADDR", "")
        self.save_path = os.environ.get("MAIL_SAVE_PATH", "")
        self.from_addr = os.environ.get("MAIL_FROM_ADDR", self.username)
        self.from_name = os.environ.get("MAIL_FROM_NAME", self.username)

    def check_env_vars(self, required_envs):
        for env in required_envs:
            if env not in os.environ or not os.environ[env]:
                raise RuntimeError(f"环境变量 {env} 未设置")

    def get_smtp_host_port(self):
        if ":" in self.smtp_addr:
            host, port = self.smtp_addr.split(":", 1)
            return host, int(port)
        return self.smtp_addr, 465

    def get_imap_host_port(self):
        if ":" in self.imap_addr:
            host, port = self.imap_addr.split(":", 1)
            return host, int(port)
        return self.imap_addr, 993

    def get_smtp_server(self):
        self.check_env_vars([
            "MAIL_USER_NAME",
            "MAIL_PASS_WORD",
            "MAIL_SMTP_ADDR",
        ])
        host, port = self.get_smtp_host_port()
        server = smtplib.SMTP_SSL(host, port)
        server.login(self.username, self.password)
        return server

    def get_imap_server(self):
        self.check_env_vars([
            "MAIL_USER_NAME",
            "MAIL_PASS_WORD",
            "MAIL_IMAP_ADDR",
        ])
        host, port = self.get_imap_host_port()
        server = imaplib.IMAP4_SSL(host, port)
        server.login(self.username, self.password)
        return server

    def decode_header_field(self, msg, field):
        import email.header
        val = msg.get(field, "")
        if not val:
            return ""
        parts = email.header.decode_header(val)
        return ''.join([
            (v.decode(enc) if isinstance(v, bytes) else v) if enc else v
            for v, enc in parts
        ])

    def save_attachments(self, msg, uid):
        import os
        attachments = []
        if msg.is_multipart():
            for part in msg.walk():
                filename = part.get_filename()
                if filename:
                    attachments.append(filename)
                if filename and self.save_path:
                    attach_dir = os.path.join(self.save_path, uid)
                    os.makedirs(attach_dir, exist_ok=True)
                    file_path = os.path.join(attach_dir, filename)
                    with open(file_path, "wb") as f:
                        f.write(part.get_payload(decode=True))
        return attachments

@mcp.tool()
def send_email(
    to: str,
    subject: str,
    content: str,
    attachments: List[str] = None
) -> Dict[str, Any]:
    """
    Send an email with optional attachments.
    Args:
        to: Recipient email address
        subject: Email subject
        content: Email body (plain text)
        attachments: List of absolute file paths to attach
    Returns:
        Dict with success status and message
    """
    try:
        client = EmailClient()
        server = client.get_smtp_server()
        msg = MIMEMultipart()
        msg['To'] = formataddr((to, to))
        msg['From'] = formataddr((client.from_name, client.from_addr))
        msg['Subject'] = subject
        msg.attach(MIMEText(content, 'plain', 'utf-8'))
        # Attach files
        if attachments:
            for file_path in attachments:
                if not os.path.isfile(file_path):
                    continue
                with open(file_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                    msg.attach(part)
        server.sendmail(client.username, [to], msg.as_string())
        server.quit()
        return {"success": True, "message": "Email sent successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
def list_inbox(
    limit: int = 10,
    start: int = 0
) -> Dict[str, Any]:
    """
    List emails in the inbox with brief information.
    Args:
        limit: Maximum number of emails to return
        start: Start index (0-based, from the latest email)
    Returns:
        Dict with a list of emails (uid, subject, snippet, date, seen, attachment)
    """
    emails: List[Dict[str, str]] = []
    try:
        client = EmailClient()
        mail = client.get_imap_server()
        mail.select('INBOX')
        typ, data = mail.search(None, 'ALL')
        mail_ids = data[0].split()
        mail_ids = mail_ids[::-1][start:start+limit]
        for num in mail_ids:
            typ, msg_data = mail.fetch(num, '(RFC822 FLAGS UID)')
            msg = email.message_from_bytes(msg_data[0][1])
            subject = client.decode_header_field(msg, 'Subject')
            date_ = client.decode_header_field(msg, 'Date')
            snippet = ""
            attachment = 0
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            charset = part.get_content_charset() or 'utf-8'
                            snippet = part.get_payload(decode=True).decode(charset, errors='ignore')
                            snippet = snippet.strip().replace('\r', '').replace('\n', ' ')
                        except Exception:
                            continue
                    if part.get_filename():
                        attachment += 1
            else:
                try:
                    charset = part.get_content_charset() or 'utf-8'
                    snippet = msg.get_payload(decode=True).decode(charset, errors='ignore')
                    snippet = snippet.strip().replace('\r', '').replace('\n', ' ')
                except Exception:
                    snippet = ""
            snippet = snippet[:120]
            typ, flag_data = mail.fetch(num, '(FLAGS)')
            seen = b'\\Seen' in flag_data[0] if flag_data and flag_data[0] else False
            typ, uid_data = mail.fetch(num, '(UID)')
            import re
            uid_match = re.search(br'UID (\d+)', uid_data[0])
            uid = uid_match.group(1).decode() if uid_match else ""
            emails.append({
                "uid": uid, "subject": subject, "snippet": snippet,
                "date": date_, "seen": seen, "attachment": attachment
            })
        mail.logout()
        return {"emails": emails}
    except Exception as e:
        return {"emails": [], "error": str(e)}

@mcp.tool()
def list_sent(
    limit: int = 10,
    start: int = 0
) -> Dict[str, Any]:
    """
    List emails in the sent mailbox with brief information.
    Args:
        limit: Maximum number of emails to return
        start: Start index (0-based, from the latest email)
    Returns:
        Dict with a list of emails (uid, subject, snippet, date, seen, attachment)
    """
    emails: List[Dict[str, str]] = []
    try:
        client = EmailClient()
        mail = client.get_imap_server()
        sent_folders = ["Sent", "Sent Mail", "Sent Messages", "已发送", "已发送邮件"]
        selected = False
        for folder in sent_folders:
            try:
                typ, _ = mail.select(folder)
                if typ == 'OK':
                    selected = True
                    break
            except Exception:
                continue
        if not selected:
            mail.logout()
            return {"emails": [], "error": "No sent folder found"}
        typ, data = mail.search(None, 'ALL')
        mail_ids = data[0].split()
        mail_ids = mail_ids[::-1][start:start+limit]
        for num in mail_ids:
            typ, msg_data = mail.fetch(num, '(RFC822 FLAGS UID)')
            msg = email.message_from_bytes(msg_data[0][1])
            subject = client.decode_header_field(msg, 'Subject')
            date_ = client.decode_header_field(msg, 'Date')
            snippet = ""
            attachment = 0
            if msg.is_multipart():
                for part in msg.walk():
                    filename = part.get_filename()
                    content_disposition = part.get("Content-Disposition", "")
                    if part.get_content_type() == "text/plain" and attachment == 0:
                        try:
                            snippet = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                            snippet = snippet.strip().replace('\r', '').replace('\n', ' ')
                        except Exception:
                            continue
                    if filename:
                        attachment += 1
            else:
                try:
                    snippet = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
                    snippet = snippet.strip().replace('\r', '').replace('\n', ' ')
                except Exception:
                    snippet = ""
            snippet = snippet[:120]
            typ, flag_data = mail.fetch(num, '(FLAGS)')
            seen = b'\\Seen' in flag_data[0] if flag_data and flag_data[0] else False
            typ, uid_data = mail.fetch(num, '(UID)')
            import re
            uid_match = re.search(br'UID (\d+)', uid_data[0])
            uid = uid_match.group(1).decode() if uid_match else ""
            emails.append({
                "uid": uid, "subject": subject, "snippet": snippet,
                "date": date_, "seen": seen, "attachment": attachment
            })
        mail.logout()
        return {"emails": emails}
    except Exception as e:
        return {"emails": [], "error": str(e)}

@mcp.tool()
def read_email(
    uid: str,
) -> Dict[str, Any]:
    """
    Read full details of an email by UID, and optionally save attachments.
    Args:
        uid: UID of the email
    Returns:
        Dict with all email fields (uid, message_id, from, to, subject, date, seen, in_reply_to, references, snippet, attachments)
    """
    import os
    try:
        client = EmailClient()
        mail = client.get_imap_server()
        mail.select('INBOX')
        typ, msg_data = mail.uid('fetch', uid, '(RFC822 FLAGS UID)')
        if not msg_data or not msg_data[0] or not isinstance(msg_data[0], tuple) or not msg_data[0][1]:
            mail.logout()
            return {"error": "Email content is empty"}
        msg = email.message_from_bytes(msg_data[0][1])
        typ, flag_data = mail.uid('fetch', uid, '(FLAGS)')
        seen = b'\\Seen' in flag_data[0] if flag_data and flag_data[0] else False
        uid_val = uid
        snippet = ""
        attachments = client.save_attachments(msg, uid)
        # 获取正文预览
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        snippet = part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8', errors='ignore')
                        snippet = snippet.strip().replace('\r', '').replace('\n', ' ')
                        break
                    except Exception:
                        continue
        else:
            try:
                snippet = msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')
                snippet = snippet.strip().replace('\r', '').replace('\n', ' ')
            except Exception:
                snippet = ""
        snippet = snippet[:120]
        detail = {
            "uid": uid_val,
            "message_id": client.decode_header_field(msg, 'Message-ID'),
            "from": client.decode_header_field(msg, 'From'),
            "to": client.decode_header_field(msg, 'To'),
            "subject": client.decode_header_field(msg, 'Subject'),
            "date": client.decode_header_field(msg, 'Date'),
            "in_reply_to": client.decode_header_field(msg, 'In-Reply-To'),
            "references": client.decode_header_field(msg, 'References'),
            "seen": seen, "snippet": snippet, "attachments": attachments
        }
        mail.logout()
        return detail
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def reply_email(
    uid: str,
    subject: str,
    content: str,
    attachments: List[str] = None
) -> Dict[str, Any]:
    """
    Reply to an email, automatically setting reply headers and supporting attachments.
    Args:
        uid: UID of the original email to reply to
        subject: Email subject
        content: Email body (plain text or HTML, auto-detected)
        attachments: List of absolute file paths to attach
    Returns:
        Dict with success status and message
    """
    try:
        client = EmailClient()
        mail = client.get_imap_server()
        mail.select('INBOX')
        typ, msg_data = mail.uid('fetch', uid, '(RFC822)')
        if not msg_data or not msg_data[0] or not isinstance(msg_data[0], tuple) or not msg_data[0][1]:
            mail.logout()
            return {"success": False, "message": "Original email content is empty"}
        msg_orig = email.message_from_bytes(msg_data[0][1])
        original_from = client.decode_header_field(msg_orig, 'From')
        original_subject = client.decode_header_field(msg_orig, 'Subject')
        original_message_id = client.decode_header_field(msg_orig, 'Message-ID')
        mail.logout()
        html_signs = ['<html', '<body', '</p>', '<div', '<span',
                      '<br', '<table', '<tr', '<td', '<!DOCTYPE html']
        is_html = any(sign in content.lower() for sign in html_signs)
        server = client.get_smtp_server()
        msg = MIMEMultipart()
        msg['From'] = formataddr((client.from_name, client.from_addr))
        msg['To'] = original_from
        msg['Subject'] = subject
        if original_message_id:
            msg['In-Reply-To'] = original_message_id
            msg['References'] = original_message_id
        if original_from:
            msg['Reply-To'] = original_from
        if original_subject:
            msg['Thread-Topic'] = original_subject
        if is_html:
            msg.attach(MIMEText(content, 'html', 'utf-8'))
        else:
            msg.attach(MIMEText(content, 'plain', 'utf-8'))
        # Attach files
        if attachments:
            for file_path in attachments:
                if not os.path.isfile(file_path):
                    continue
                with open(file_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                    msg.attach(part)
        server.sendmail(client.username, [original_from], msg.as_string())
        server.quit()
        return {"success": True, "message": "Reply email sent successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def main():
    mcp.run(show_banner=False)

if __name__ == "__main__":
    main()
