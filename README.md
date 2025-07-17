# MCP Email Client

A Model Context Protocol (MCP) server for sending and receiving emails, supporting IMAP/SMTP, with display name, reply, robust error handling, and full attachment support.

## Features
- Send emails (with display name and attachment support)
- List inbox/sent emails (brief info, attachment count)
- Read email details by UID (auto-save and list attachments)
- Reply to emails (auto set headers, display name, attachments)
- Environment variable based configuration
- Robust error handling and IMAP/SMTP compatibility

## Example JSON config for MCP/Claude/Inspector
This format is suitable for use with Claude Desktop, MCP Inspector, or any MCP client that supports multi-server JSON configuration:

```json
{
  "mcpServers": {
    "mcp-email-client": {
      "command": "uvx",
      "args": [
        "mcp-email-client"
      ],
      "env": {
        "MAIL_USER_NAME": "your@email.com",
        "MAIL_PASS_WORD": "yourpassword",
        "MAIL_SMTP_ADDR": "smtp.example.com:465",
        "MAIL_IMAP_ADDR": "imap.example.com:993",
        "MAIL_FROM_NAME": "Your Name",
        "MAIL_FROM_ADDR": "your@email.com",
        "MAIL_SAVE_PATH": "/absolute/path/to/attachments"
      }
    }
  }
}
```

- You can add multiple servers under `mcpServers`.
- This config can be loaded directly by Claude Desktop, MCP Inspector, or compatible tools.

## Environment Variables
| Name              | Description                        | Example                  |
|-------------------|------------------------------------|--------------------------|
| MAIL_USER_NAME    | Email account (login username)     | user@example.com         |
| MAIL_PASS_WORD    | Email account password/app token   | yourpassword             |
| MAIL_SMTP_ADDR    | SMTP host:port                     | smtp.example.com:465     |
| MAIL_IMAP_ADDR    | IMAP host:port                     | imap.example.com:993     |
| MAIL_FROM_ADDR    | (Optional) From email address      | user@example.com         |
| MAIL_FROM_NAME    | (Optional) From display name       | Alice                    |
| MAIL_SAVE_PATH    | (Optional) Path to save attachments| /absolute/path/to/dir    |

## Installation

```bash
uv pip install fastmcp
# or
pip install fastmcp
```

## Usage

1. Set environment variables (see above)
2. Run the server:

```bash
python server.py
```

## API Endpoints (Tools)

### send_email
Send an email, with optional attachments.
- Args:
    - `to`: Recipient email address
    - `subject`: Email subject
    - `content`: Email body (plain text)
    - `attachments`: List of absolute file paths to attach (optional)
- Returns: `{ "success": bool, "message": str }`

### reply_email
Reply to an email, with optional attachments.
- Args:
    - `uid`: UID of the original email to reply to
    - `subject`: Email subject
    - `content`: Email body (plain text or HTML)
    - `attachments`: List of absolute file paths to attach (optional)
- Returns: `{ "success": bool, "message": str }`

### list_inbox / list_sent
List inbox or sent emails (brief info, attachment count).
- Args:
    - `limit`: Maximum number of emails to return (default 10)
    - `start`: Start index (0-based, from the latest email)
- Returns: `{ "emails": [ { "uid", "subject", "snippet", "date", "seen", "attachment" } ] }`
    - `attachment`: Number of attachments in the email

### read_email
Read full details of an email by UID, auto-save and list attachments.
- Args:
    - `uid`: UID of the email
- Returns: `{ "uid", "message_id", "from", "to", "subject", "date", "seen", "in_reply_to", "references", "snippet", "attachments" }`
    - `attachments`: List of all attachment filenames (auto-saved to MAIL_SAVE_PATH/uid/ if MAIL_SAVE_PATH is set)

## Example .env
```
MAIL_USER_NAME=your@email.com
MAIL_PASS_WORD=yourpassword
MAIL_SMTP_ADDR=smtp.example.com:465
MAIL_IMAP_ADDR=imap.example.com:993
MAIL_FROM_NAME=Your Name
MAIL_FROM_ADDR=your@email.com
MAIL_SAVE_PATH=/absolute/path/to/attachments
```

## FAQ
- **Q: Why do I get 'Email content is empty'?**
  - A: The UID may not exist, or the email was deleted/moved. Make sure to use a valid UID from list_inbox/list_sent.
- **Q: How to set display name?**
  - A: Set MAIL_FROM_NAME in your environment variables.
- **Q: How to send HTML email?**
  - A: Just include HTML tags in content, the server will auto-detect and set the correct MIME type.
- **Q: How to send attachments?**
  - A: Pass a list of absolute file paths to the `attachments` parameter in send_email or reply_email.
- **Q: How to auto-save received attachments?**
  - A: Set MAIL_SAVE_PATH. All attachments will be saved to MAIL_SAVE_PATH/uid/ when reading emails.

## License
MIT