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
from imapclient import imap_utf7
import extract_msg
import PyPDF3
import textract
import shutil
import nltk.tokenize as tk

from wccia import collector
from wccia import configuration_file as config

from nltk.corpus import stopwords

stopWords = set(stopwords.words('english'))

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
        self.create_date = None;
        self.text = None;
        self.body_clean = None;
        self.name = None;
        self.ID = None;
        self.content_language = None;
        self.accept_language = None;
        self.in_reply_to = None;
        self.references = None;
        self.atts = None;
        self.original_msg = None;

class Parser(object):   

    def __init__(self):
        connection = None
        rfq_instances = []
        test_mode = 'OFF'
        self.coll = collector.BD()
        self.minio_bucket = config.conf['MINIO_BUCKET']
        self.path_to_dir = ''

    def set_test_mode(self, mode):
        '''Se mode for OFF, normal. Se ON, não grava as infos.'''
        self.test_mode = mode
        
    def get_test_mode(self):
        return self.test_mode

    def list_mailboxes(self, conn):
        rv, mailboxes = conn.list()
        print('LISTA DE MAIL BOXES:')
        for i in mailboxes:
            decoded = imap_utf7.decode(i)            
            print('')
            if isinstance(decoded, str):
                
                sp = decoded.split("\"/\"")[-1]
                print(sp)
    
    def select_mailbox(self, conn, mail_box):
        try:
            rv, data = conn.select(mail_box)                        
        except imaplib.IMAP4.error:
            print ("Unable to open mailbox ")
           
        
    def connect(self, server, login, password):                        
        try:
            self.connection = imaplib.IMAP4_SSL(server)
        except imaplib.IMAP4.error:            
            print ("Failed! ")
            sys.exit(1)
        try:
            self.connection.login(login, password)
        except imaplib.IMAP4.error:            
            print ("login, psw Failed! ")
            sys.exit(1)
        try:
            self.connection.select(readonly=False)            
        except imaplib.IMAP4.error:            
            print ("select Failed! ")
            sys.exit(1)

        return self.connection
        
    def process_mailbox(self, conn, search):        
        
        rv, data = conn.search(None, search) # 'SEEN', 'UNSEEN', etc...
        mail_list = []
        black_list = ['wf-batch <wf-batch@weg.net>'] 

        if rv != 'OK':
            print("No messages found!")
            return

        for num in data[0].split():
           
            subject = ""
            to = ""
            sender = ""
            date = ""
            create_date = ""
            body = ""
            message_ID = ""
            in_reply_to = ""
            references = "" 
            content_language = ""
            accept_language = ""
            has_att = False            
            attach = []            
            
            rfq_id = uuid.uuid1() # identificador do email. Usado para compor o path            
            
            rv, data = conn.fetch(num, '(RFC822)')
            if rv != 'OK':
                print ("ERROR getting message")
                return
            
            msg = email.message_from_bytes(data[0][1])    
            
            #Dados do email -------
            if(msg['from']):
                sender = msg['from']

            if sender not in black_list:

                if(msg['Message-ID']):
                    message_ID = msg['Message-ID']
                if(msg['In-Reply-To']):
                    in_reply_to = msg['In-Reply-To']
                if(msg['References']):                
                    references = msg['References']
                if(msg['Accept-Language']):                
                    accept_language = msg['Accept-Language']
                if(msg['Content-Language']):                
                    content_language = msg['Content-Language']
                     
                self.path_to_dir = str(rfq_id) 

                if not os.path.exists(self.path_to_dir):                
                    os.makedirs(self.path_to_dir) # se não existe: cria
            
                smsg = msg.as_bytes().decode(encoding='ISO-8859-1') # essa é mensagem original pronta para ser gravada na pasta
                name = 'original_msg.eml'
                smsg_path = os.path.join(self.path_to_dir, name)
                smsg_path = smsg_path.replace('\\', '/')
                            
                if(msg['Subject']):
                    subject = msg['Subject']
                    subject, encoding = email.header.decode_header(subject)[0]                
                    if not isinstance(subject, str):                    
                        subject = subject.decode(encoding)                               
                if(msg['to']):
                    to = msg['to']
                                        
                date_tuple = email.utils.parsedate_tz(msg['Date'])            
                if date_tuple:
                    local_date = datetime.datetime.fromtimestamp(
                        email.utils.mktime_tz(date_tuple))
                    date = datetime.datetime.strptime(str(local_date), "%Y-%m-%d %H:%M:%S")

                create_date = datetime.datetime.now()
                    
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
                            body_clean = self.pre_process(body)
                            body_clean = str.encode(body_clean) # encode to bytes a string                    
 
                            
                        if ctype == 'text/html':
                            #html = str(part.get_payload(decode=True), str(charset), "ignore").encode('ANSI', 'ignore')
                            if charset != None:
                                html = str(part.get_payload(decode=True), str(charset), "ignore")
                            else:
                                html = str(part.get_payload(decode=True))
                                
                            body = self.text_from_html(html)
                            body_clean = self.pre_process(body)
                            body_clean = str.encode(body_clean) # encode to bytes a string 
                            
                        if cdispo is not None:
                            if (dispo_type == 'attachment') and ctype.split('/')[0] != 'message':
                                #é um anexo e não é uma mensagem (rfc822); Para incluir partes não textuais do corpo do email: dispo_type == 'inline'

                                attachment = Attachment();
                                attachment.data = part.get_payload(decode=True);
                                attachment.content_type = part.get_content_type();
                                attachment.size = len(attachment.data);
                                attachment.name = part.get_filename();                            
                                attachment.name = re.sub('[\n\r]', '', attachment.name)                            
                                attachment.name = os.path.join(self.path_to_dir, attachment.name)
                                attachment.name = attachment.name.replace('\\', '/')

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
                    body_clean = self.pre_process(body) 
                    body_clean = str.encode(body_clean) # encode to bytes a string              

                
                #i = '[^0-9a-zA-Z]+'            
                #sufixo = re.sub(i, '', subject)
                #sufixo = unicodedata.normalize('NFKD', sufixo).encode('ascii', 'ignore')
                #sufixo = sufixo.decode()

                #for x in sufixo.split(' '):
                #    os.path.join(sufixo, x)
                #name = sufixo  + '_body.txt'            
                name = '_body.txt'
                abspath = os.path.join(self.path_to_dir, name) # compõe nome do body 
                abspath = abspath.replace('\\', '/')

                # Agora compõe os dados em uma classe
                mail_infos = MailInfos();
                mail_infos.to = to
                mail_infos.sender = sender
                mail_infos.subject = subject
                mail_infos.date = date
                mail_infos.create_date = create_date
                mail_infos.text = body 
                mail_infos.body_clean = body_clean
                mail_infos.name = abspath
                mail_infos.ID = message_ID 
                mail_infos.accept_language = accept_language
                mail_infos.content_language = content_language                           
                mail_infos.in_reply_to = in_reply_to;
                mail_infos.references = references;
                mail_infos.original_msg = (smsg, smsg_path);
                if(has_att):
                    mail_infos.atts = attach                
                    has_att = False

                mail_list.append(mail_infos);

                if self.test_mode == 'OFF':
                    erro = False

                    try:
                        self.save_file(mail_infos) # salva o body e a mensagem
                        self.save_attachments(mail_infos) # salva anexos
                        self.save_database(mail_infos) # salva no banco

                        shutil.rmtree(self.path_to_dir, ignore_errors=True)
                    except:
                        erro = True

                    if erro == True:
                        #TO DO funcao que reverte os saves
                        erro = False

        return mail_list
            
    def parse_email(self, msg):
        ''' Carrega uma mensagem atraves de arquivo
        
        Output: Objeto Mail com subject, data, body, caminho dos anexos
        '''
        
        infos = MailInfos();

        msg = extract_msg.Message(msg)
        
        attach = []
        infos = MailInfos();
        
        count_attachments = len(msg.attachments)
        if count_attachments > 0:          
            for item in msg.attachments:
                attach.append(item.longFilename)                
                #print(item.save())
                

        infos.subject = msg.subject
        infos.date = msg.date
        infos.text = msg.body                   
        infos.atts = attach
        infos.ID = msg.message_id
        infos.in_reply_to = msg.reply_to

        msg.close()
        
        return infos


    def check_doc(self, file):
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

        conn = self.coll.connect_mongo()

        #conn = MongoClient('mongodb://'+ conf['DB_SERVER'] + ':' + )        
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
            "anexos": { "body_txt": body_bytes, "attchs": atts_url, "original_msg": data.original_msg[1], "body_link": data.name, "body_clean": data.body_clean },
            "create_date" : data.create_date,
            "content_language" : data.content_language,
            "accept_language" : data.accept_language
            }
            
        db.quotations.insert_one(rfq);
        self.coll.disconnet_mongo(conn)
     
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
        minio = self.coll.connect_minio()

        if data.atts != None:
            for att in data.atts:                    
                file = open(att.name, 'wb');
                file.write(att.data);
                file.close();

                self.coll.put_object(minio, att.name, att.name)
                    
    def save_file(self, data):                          
        minio = self.coll.connect_minio()

        body_path = data.name
        message_path = data.original_msg[1]

        #body
        file = open(body_path, 'w', encoding='utf-8');            
        file.write(data.text);
        file.close();

        #mensagem original
        file = open(message_path, 'w', encoding='utf-8');            
        file.write(data.original_msg[0]);
        file.close();

        #envia os arquivos para o object storage               
        self.coll.put_object(minio, body_path, body_path)       
        self.coll.put_object(minio, message_path, message_path)

        #compacta a mensagem
        '''
        new_name = data.original_msg[1][:-3] + 'zip'
        zip_file = zipfile.ZipFile(new_name, 'w')
        zip_file.write(data.original_msg[1], compress_type=zipfile.ZIP_DEFLATED)
        os.remove(data.original_msg[1])
        zip_file.close()
        '''

    def tag_visible(self, element):
        if element.parent.name in ['style', 'font', 'script', 'head', 'title', 'meta', '[document]']:
            return False
        if isinstance(element, Comment):
            return False
        return True

    def ext_span(self,body):
        '''Elimina texto de footer, e outros lixos'''        
        soup = BeautifulSoup(body, 'html.parser')      

        for data in soup.select('span'):
            if 'font-size' in str(data):
                size = re.search(r'(?is)(font-size:)(.*?)(pt)',str(data.get('style')))
                if size is not None:
                    size = size.group(2).strip()
                    if (float(size) < 9.5):
                        data.extract()
        
        for data in soup.select('font'):
            if 'size' in str(data):                
                size = re.search(r'(size=)([\"\']\d[\"\'])',str(data))
                if size is not None:                    
                    size = size.group(2).strip()[1]                      
                    if (int(size) <= 1):                        
                        data.extract()   
        return soup        

    def pre_process(self, txt):
        regex_email = r"\<*\s*(\S+)\@(\S+)\.(\S+)\s*\>*"

        txt = re.sub(regex_email, '', txt)        
        words = tk.word_tokenize(txt)
        k = [s.lower() for s in words]
        txt = " ".join(w for w in k if w not in stopWords)

        return txt

    def text_from_html(self,body):
        soup = self.ext_span(body)        
        texts = soup.findAll(text=True)
        visible_texts = filter(self.tag_visible, texts)         
        count = 0
        txt = ""
        tx = []

        #elimina new lines excessivas.
        for t in visible_texts:            
            for g in t.splitlines():                
                if g == '':                       
                    if count == 1:
                        pass
                    else:
                        count = 1
                        tx.append(t)                        
                else:                    
                    tx.append(t)                        
                    count = 0

        txt = "".join(t for t in tx) 

        return txt