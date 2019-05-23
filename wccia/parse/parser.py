# -*- coding: utf-8 -*-
import email
import email.header
import imaplib
import datetime
import sys
import os
from bs4 import BeautifulSoup
from bs4.element import Comment
import re
import uuid
from pymongo import MongoClient
from imapclient import imap_utf7
import extract_msg
import unicodedata
import PyPDF3
import textract
import json
from . import configuration_file as conf

class Attachment(object):

    def __init__(self):
        self.data = None;
        self.content_type = None;
        self.size = None;        
        self.name = None;
    
class MailInfos(object):

    def __init__(self):
        self.to = None;
        self.sender = None;
        self.subject = None;
        self.date = None;
        self.text = None;
        self.name = None;
        self.ID = None;
        self.in_reply_to = None;
        self.references = None;
        self.atts = None;


class Parser(object):

    connection = None
    rfq_instances = []

    def __init__(self, server, login, password):
        
        self.server = server
        self.login = login
        self.password = password

    def list_mailboxes(self, conn):
        rv, mailboxes = conn.list()
        print('LISTA DE MAIL BOXES:')
        for i in mailboxes:
            decoded = imap_utf7.decode(i)            
            print('')
            print(decoded.split("\"/\"")[1])
    
    def select_mailbox(self, conn, mail_box):
        try:
            rv, data = conn.select(mail_box)
            print (rv, data)            
        except imaplib.IMAP4.error:
            print ("Unable to open mailbox ", rv)
           
        
    def connect(self):
                
        try:
            self.connection = imaplib.IMAP4_SSL(self.server)
            self.connection.login(self.login, self.password)
            self.connection.select(readonly=False)
            print('Connected!')
        except imaplib.IMAP4.error:            
            print ("Failed! ")
            sys.exit(1)

        return self.connection
        

    def process_mailbox(self, conn, search):
        
        root_folder = conf['NAS_FOLDER']
        rv, data = conn.search(None, search) # 'SEEN', 'UNSEEN', etc...

        if rv != 'OK':
            print("No messages found!")
            return

        for num in data[0].split():
           
            subject = ""
            to = ""
            sender = ""
            date = ""
            body = ""
            message_ID = ""
            in_reply_to = ""
            references = ""
            path_to_dir = ""
            has_att = False            
            attach = []            
            rfq_id = uuid.uuid1() # identificador do email. Usado para compor o path            
            
            rv, data = conn.fetch(num, '(RFC822)')
            if rv != 'OK':
                print ("ERROR getting message")
                return
            
            msg = email.message_from_bytes(data[0][1])

            #Dados do email -------
            message_ID = msg['Message-ID']
            in_reply_to = msg['In-Reply-To']
            references = msg['References']
                                  
            path_to_dir = root_folder + '\\' + str(rfq_id) 

            if not os.path.exists(path_to_dir):
                os.makedirs(path_to_dir) # se não existe: cria
                        
            if(msg['Subject']):
                subject = msg['Subject']
                subject, encoding = email.header.decode_header(subject)[0]                
                if not isinstance(subject, str):                    
                    subject = subject.decode(encoding)                               
            if(msg['to']):
                to = msg['to']
            if(msg['from']):
                sender = msg['from']
                        
            date_tuple = email.utils.parsedate_tz(msg['Date'])            
            if date_tuple:
                local_date = datetime.datetime.fromtimestamp(
                    email.utils.mktime_tz(date_tuple))
                date = datetime.datetime.strptime(str(local_date), "%Y-%m-%d %H:%M:%S")
                
            #-----------------------------
              
            #Anexos do email -------            
            if msg.is_multipart():
                for part in msg.walk():
      
                    ctype = part.get_content_type()
                    cdispo = str(part.get('Content-Disposition'))
                    dispo_type = str(part.get_content_disposition())
                    charset = part.get_content_charset()

                    if ctype == 'text/plain':                      
                        #text = str(part.get_payload(decode=True), str(charset), "ignore").encode('ANSI', 'replace')
                        if charset != None:
                            text = str(part.get_payload(decode=True), str(charset), "ignore")
                        else:
                            text = str(part.get_payload(decode=True))
                        body = text
                        
                    if ctype == 'text/html':
                        #html = str(part.get_payload(decode=True), str(charset), "ignore").encode('ANSI', 'ignore')
                        if charset != None:
                            html = str(part.get_payload(decode=True), str(charset), "ignore")
                        else:
                            html = str(part.get_payload(decode=True))
                            
                        body = self.text_from_html(html)
                        
                    if cdispo is not None:
                        if (dispo_type == 'attachment') and ctype.split('/')[0] != 'message':
                            #é um anexo e não é uma mensagem (rfc822); Para incluir partes não textuais do corpo do email: dispo_type == 'inline'

                            attachment = Attachment();
                            attachment.data = part.get_payload(decode=True);
                            attachment.content_type = part.get_content_type();
                            attachment.size = len(attachment.data);
                            attachment.name = part.get_filename();                            
                            attachment.name = re.sub('[\n\r]', '', attachment.name)
                            attachment.name = os.path.join(path_to_dir, attachment.name)

                            if re.search('(\w+[.]\w+)', attachment.name) != None : #confere se é um arquivo com extenção
                                if attachment.name[-2:] != "?=":
                                    attach.append(attachment);
                                    has_att = True
                        
            else:
                charset = msg.get_content_charset()
                if charset != None:
                    html = str(msg.get_payload(decode=True), str(charset), "ignore")
                else:
                    html = str(msg.get_payload(decode=True))
                    
                body = self.text_from_html(html)                

            
            i = '[^0-9a-zA-Z]+'            
            sufixo = re.sub(i, '', subject)
            sufixo = unicodedata.normalize('NFKD', sufixo).encode('ascii', 'ignore')
            sufixo = sufixo.decode()

            for x in sufixo.split(' '):
                os.path.join(sufixo, x)
            name = sufixo  + '_body.txt'            
            abspath = os.path.join(path_to_dir, name) # compõe nome do body 

            # Agora compõe os dados em uma classe
            mail_infos = MailInfos();
            mail_infos.to = to
            mail_infos.sender = sender
            mail_infos.subject = subject
            mail_infos.date = date
            mail_infos.text = body           
            mail_infos.name = abspath
            mail_infos.ID = message_ID            
            mail_infos.in_reply_to = in_reply_to;
            mail_infos.references = references;
            if(has_att):
                mail_infos.atts = attach                
                has_att = False

            #mail_inf.append(mail_infos);

            self.save_file(mail_infos) # salva o body
            self.save_attachments(mail_infos) # salva anexos
            self.save_database(mail_infos) # salva no banco
            
    def parse_email(self, msg):

        mail_infos = MailInfos();

        msg = extract_msg.Message(msg)

        attach = []
        mail_infos = MailInfos();
        
        count_attachments = len(msg.attachments)
        if count_attachments > 0:          
            for item in msg.attachments:
                attach.append(item.longFilename)                
                #print(item.save())
                

        mail_infos.subject = msg.subject
        mail_infos.date = msg.date
        mail_infos.text = msg.body                   
        mail_infos.atts = attach
        
        return mail_infos


    def check_doc(file):
        with open(file, 'rb') as testMe:
            startBytes = testMe.read(2).decode('latin1')
            print (startBytes)
            if startBytes == 'PK':
                return 'DOCX'
            else:
                return 'DOC'

    
    def close_connection(self, conn):
        conn.close()

    def save_database(self, data):

        atts_url = []

        conn = MongoClient('mongodb://'+ conf['DB_SERVER'] + ':' + conf['DB_PORT'])        
        db = conn.emailClassifier
              
        body_bytes = str.encode(data.text) # encode to bytes a string                    


        if(data.atts != None):
            for j in range(len(data.atts)):
                atts_url.append(data.atts[j].name)
 
        #cria um document (JSON)
        rfq = {
            "message_ID": data.ID,
            "in_reply_to": data.in_reply_to,
            "references": data.references,
            "sender": data.sender,
            "receiver": data.to,
            "subject": data.subject,
            "date": data.date,
            "anexos": { "body_txt": body_bytes, "attchs": atts_url  }
            }
            
        db.quotations.insert_one(rfq);
        conn.close();
        

    def extract_data_from_file(self,data_file):
        text=""
        try:
            text = textract.process(data_file)
        except:
            print('File format not supported')
            pass
        return text

    def extract_data_from_pdf(self,pdf_file):
        page_content = ""
        pdfFileObj = open(pdf_file,'rb')
        pdfReader = PyPDF3.PdfFileReader(pdfFileObj)
        number_of_pages = pdfReader.getNumPages()
        for page_number in range(number_of_pages):
            page = pdfReader.getPage(page_number)
            page_content = page_content + page.extractText()   
        return page_content

    def save_attachments(self, data):          
        if data.atts != None:
            for att in data.atts:                    
                file = open(att.name, 'wb');
                file.write(att.data);
                file.close();
                    
    def save_file(self, data):                          
        file = open(data.name, 'w', encoding='utf-8');            
        file.write(data.text);
        file.close();

    def tag_visible(self, element):
        if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
            return False
        if isinstance(element, Comment):
            return False
        return True

    def text_from_html(self,body):
        soup = BeautifulSoup(body, 'html.parser')
        texts = soup.findAll(text=True)
        visible_texts = filter(self.tag_visible, texts)  
        return u" ".join(t.strip() for t in visible_texts)
