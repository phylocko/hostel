import smtplib
from email.mime.text import MIMEText
from hostel.settings import EMAIL_FROM


class MailError(Exception):
    pass


def email_admin(mail_to, message_subject, message_text):
    """
    Shortcut to email_someone with mail_from=settings.EMAIL_FROM
    """
    email_someone(mail_to, EMAIL_FROM, message_subject, message_text)


def email_someone(mail_to, mail_from, message_subject, message_text):
    """
    Sending an email. extensions must be caught and processed in local code
    :param mail_to: 'user@mail.ru' or 'user1@mail.ru, user2@mail.ru'
    :param mail_from: address of sender. settings.EMAIL_FROM by default
    :param message_subject: subject of the message
    :param message_text: message body (plain text)
    :return: None
    """
    try:
        s = smtplib.SMTP('localhost')
    except Exception as e:
        raise MailError(e)

    message = MIMEText(message_text)
    message['Subject'] = message_subject
    message['From'] = mail_from or EMAIL_FROM
    message['To'] = mail_to
    try:
        s.send_message(message)
    except Exception as e:
        raise MailError(e)
    finally:
        s.close()
