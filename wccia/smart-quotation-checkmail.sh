function check_error() {

if [ `echo $?` -eq 1 ] ;\
 then echo -e '\033[01;32mpython with errors\033[00;37m'; \
        tput sgr0 ; \
        echo "python script with error - Please Contact Gunter Herweg gunterh@weg.net" | mail -s 'mailcheck - ISSUE' gunterh@weg.net ;\
        exit 1 ; \
fi

}

if [ `docker ps -a | grep SMART_QUOTATION_WEB |wc -l` -eq "0" ] ;\
    then echo "creating docker:"; \
    docker run \
            -d \
            -p 17200:3000 \
            -e "MONGODB_CONNECTION_STRING=mongodb://10.0.12.44:43001/chatbot" \
            -e "CONTAINERNAME=SMART_QUOTATION_WEB" \
            --log-driver=splunk \
            --log-opt splunk-insecureskipverify=true \
            --log-opt splunk-token=BD383468-36A9-4540-9DAD-031B4BF10358 \
            --log-opt splunk-url=https://Brjgs772.weg.net:8088 \
            --log-opt tag=SMART_QUOTATION_WEB \
            --log-opt env=CONTAINERNAME \
            --net=host \
            --name="SMART_QUOTATION_WEB" \
            --restart=on-failure:2 \
            wegregistry:5000/smart-quotation-webapp:latest; \
            docker exec -it SMART_QUOTATION_WEB python3 /opt/smart-quotation/apps/check/check_pipe.py -m off; \
            check_error ;\
elif [ "`docker ps -a --filter "status=exited" |grep SMART_QUOTATION_WEB |wc -l`" = "1" ] ;\
     then echo "STARTING: SMART_QUOTATION_WEB on dockername:" ; docker start SMART_QUOTATION_WEB ;\
     docker exec -it SMART_QUOTATION_WEB python3 /opt/smart-quotation/apps/check/check_pipe.py -m off; \
     check_error ;\
 else 
     docker exec -it SMART_QUOTATION_WEB python3 /opt/smart-quotation/apps/check/check_pipe.py -m off; \
     check_error ;\
fi
