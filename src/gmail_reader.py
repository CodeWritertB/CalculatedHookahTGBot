"""
Simple Gmail reader using IMAP to fetch verification codes.

Requires an app password for Gmail (if using 2FA) or IMAP enabled.
"""
import imaplib
import email
import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def fetch_verification_code(gmail_user: str, gmail_password: str, senders: List[str] = None, subject_keywords: List[str] = None, search_limit: int = 50) -> Optional[str]:
    """Connects to Gmail via IMAP and searches recent emails for a numeric code.

    Args:
        gmail_user: email address
        gmail_password: app password or email password (app password recommended)
        senders: list of sender email substrings to filter (optional)
        subject_keywords: list of keywords to filter subject (optional)
        search_limit: how many recent emails to scan

    Returns:
        First found numeric code (4-8 digits) or None
    """
    senders = senders or ["instagram.com", "facebookmail.com", "accounts.google.com"]
    subject_keywords = subject_keywords or ["code", "verification", "security", "код", "верификация"]

    try:
        imap_host = 'imap.gmail.com'
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(gmail_user, gmail_password)
        mail.select('inbox')

        # search all, then fetch recent ids
        status, data = mail.search(None, 'ALL')
        if status != 'OK':
            logger.warning('IMAP search failed: %s', status)
            mail.logout()
            return None

        ids = data[0].split()
        if not ids:
            mail.logout()
            return None

        # iterate newest first
        for msg_id in reversed(ids[-search_limit:]):
            status, msg_data = mail.fetch(msg_id, '(RFC822)')
            if status != 'OK':
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            frm = msg.get('From', '')
            subj = msg.get('Subject', '')

            # filter by sender and subject
            if senders and not any(s in frm.lower() for s in senders):
                # allow if subject contains keywords
                if subject_keywords and not any(k.lower() in subj.lower() for k in subject_keywords):
                    continue

            # get payload text
            body = ''
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    cdisp = str(part.get('Content-Disposition'))
                    if ctype == 'text/plain' and 'attachment' not in cdisp:
                        try:
                            body = part.get_payload(decode=True).decode(errors='ignore')
                        except Exception:
                            body = ''
                        break
            else:
                try:
                    body = msg.get_payload(decode=True).decode(errors='ignore')
                except Exception:
                    body = ''

            text = subj + '\n' + (body or '')
            # search for 4-8 digit codes
            m = re.search(r"\b(\d{4,8})\b", text)
            if m:
                code = m.group(1)
                logger.info('Найден код в письме From=%s Subject=%s', frm, subj)
                mail.logout()
                return code

        mail.logout()
    except Exception as e:
        logger.exception('Ошибка доступа к Gmail: %s', e)

    return None
