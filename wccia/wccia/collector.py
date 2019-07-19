from pymongo import MongoClient
import pymongo
from wccia import configuration_file as config
from bson.objectid import ObjectId
from minio import Minio
from minio.error import ResponseError
from datetime import timedelta
import re
import sys
import json

class BD(object):

    def connect_minio(self):
        minio_conn = None;
        try:
            minio_conn = Minio(config.conf['MINIO_SERVER'] + ':' + config.conf['MINIO_PORT'],
                   access_key=config.conf['MINIO_USER'],
                   secret_key=config.conf['MINIO_PSW'],
                   secure=False)
        except:
            print("Cannot connect to Minio")
        
        return minio_conn

    def get_object_url(self, m_conn, obj_path):
        url = None;
        '''Retorna uma url do objeto requerido

            Parameters:
            obj_path: caminho do objeto no servidor (pasta/obj)
            conn: connection for minio

            Output:
            link para a mensagem
        '''
        try:
            url = m_conn.presigned_get_object('quotations', obj_path, expires=timedelta(days=7))
        except ResponseError as err:
            print(err)
        
        return url

    def get_object(self, m_conn, obj_path, dest_path):
        '''Retorna o objeto requerido

            Parameters:
            obj_path: caminho do objeto no servidor (pasta/obj)
            dest_path: caminho no sistema sistema local
            conn: connection for minio

            Output:
            o objeto
        '''
        try:
            m_conn.fget_object('quotations', obj_path, dest_path)
        except ResponseError as err:
            print(err)

    def put_object(self, m_conn, obj_path, dest_path):
        '''Insere o objeto no bucket

            Parameters:
            obj_path: caminho do objeto no servidor (pasta/obj)
            conn: connection for minio

            Output:
            o objeto
        '''
        try:     
           m_conn.fput_object('quotations', obj_path, dest_path)
        except ResponseError as err:
           print(err)
                
    def connect_mongo(self):
        conn = None;
        try:            
            conn = MongoClient('mongodb://' + config.conf['DB_SERVER'] + ":" + config.conf['DB_PORT'])
        except:
            print("Mongo not connected")

        return conn

    def disconnet_mongo(self, conn):
        conn.close()

    def get_original_message(self, conn, _id):
        '''Retorna a mensagem original no formato EML

            Parameters:
            _id: identifidor da rfq.
            conn: connection for BD

            Output:
            link para a mensagem
        '''

        db = conn.emailClassifier
        match = db.quotations.find({ "_id":_id }, {"_id":0, "anexos.original_msg":1})
        
        return match
    
 
    def get_email_data(self, conn, _id):
        '''Retorna informa��es sobre uma RFQ do banco

            Parameters:
            _id: identifidor da rfq.

            Output:
            Cursor com as infos sobre a rfq
        '''
           
        db = conn.emailClassifier
        match = db.quotations.find({ "_id":_id }, {"_id":0, "in_reply_to":1, "references":1, "message_ID":1, "sender":1, "receiver":1, "subject":1, "date":1, "anexos.body_txt":1, "anexos.attchs":1, "anexos.original_msg":1, "anexos.body_link":1})
        
        return match

    def get_email_data_msgID(self, conn, _id):
        '''Retorna informa��es sobre uma RFQ do banco

            Parameters:
            _id: identifidor da mensagem.

            Output:
            Cursor com as infos sobre a rfq
        '''
           
        db = conn.emailClassifier
        match = db.quotations.find({ "message_ID":_id }, {"_id":0, "in_reply_to":1, "references":1, "message_ID":1, "sender":1, "receiver":1, "subject":1, "date":1, "anexos.body_txt":1, "anexos.attchs":1, "anexos.original_msg":1, "anexos.body_link":1})
        
        return match

    def get_data_from_bd(self, conn):
        '''
        Retorna um vetor com todos as infos dos campos selecionados de todo o banco: subject, body, attch        
        '''
        vecs = []        
        
        db = conn.emailClassifier
        
        for record in db.quotations.find({}, { "in_reply_to":1, "references":1, "message_ID":1, "sender":1, "receiver":1, "subject":1, "date":1, "anexos.body_txt":1, "anexos.attchs":1, "anexos.original_msg":1, "anexos.body_link":1, "anexos.body_clean":1 }):                    
            vecs.append([record["_id"], record["subject"], record["anexos"]["body_txt"],record["anexos"]["attchs"], record["in_reply_to"], record["references"], record["message_ID"], record["sender"], record["receiver"], record["date"], record["anexos"]["original_msg"], record["anexos"]["body_link"],record["anexos"]["body_clean"]]) 

        return vecs
    
    def get_log_data(self, conn):
        '''
        Retorna os dados de log de matches.
        '''        
        db = conn.emailClassifier
        match = db.logs.find({})        
        return match

    def update_log(self, conn, minio_link, status):
        _id = re.search(r'(\w+)(-)(\w+)(-)(\w+)(-)(\w+)(-)(\w+)', minio_link)
        db = conn.emailClassifier
        db.logs.update_one(
            {'id': _id},
            {'$set': { "status": status }}            
        )

    def add_log(self, conn, new_data):
        db = conn.emailClassifier
        db.logs.insert_one(new_data)

    def remove_log(self, conn, minio_link):
        _id = re.search(r'(\w+)(-)(\w+)(-)(\w+)(-)(\w+)(-)(\w+)', minio_link)                   
        db = conn.emailClassifier
        db.logs.delete_one({'id': _id})

    def parse_log(self):

        '''Retorna informacoes sobre o log de matches

            Formato do log: Pode possuir linha com informações de data e linhas com informaçoes de match, sempre com duas mensagens (original e match)

            aaa-mm-dd hh-mm
            ('<message_id_1>', '<message_id_2>')
            
        '''
        list_of_links = []        
        #block_list = ['wf-batch <wf-batch@weg.net>'] #lista de emails que não devem entrar no log
        
        mongo = self.connect_mongo()                      
        data = self.get_log_data(mongo)
   
        for doc in data:                                                
            if doc["status"] == "":
                row = []
                data1 = doc["data1"]
                data2 = doc["data2"]
                subject1 = doc["subject1"]
                subject2 = doc["subject2"]
                link1 = doc["link1"]
                link2 = doc["link2"]
                body1 = doc["body1"]
                body2 = doc["body2"]
            
                row.append([data1, link1, subject1, data1, body1])
                row.append([data2, link2, subject2, data1, body2])
                    
                list_of_links.append(row)
        
        json_data = json.dumps(list_of_links)  
        #sys.stdout.write(json_data)
        return json_data


    
