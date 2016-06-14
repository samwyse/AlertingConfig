FROM alpine:3.2
MAINTAINER Sam Denton <samwyse@gmail.com>
EXPOSE 80

RUN apk update
RUN apk add graphviz 
RUN apk add ttf-dejavu
RUN apk add python3
RUN pip3 install --upgrade pip
RUN pip3 install graphviz

ADD src .

## CMD [ "python3", "-u", "report.py", "--port", "80" ]
ENTRYPOINT [ "python3", "-u" ]
CMD [ "report.py", "--port", "80" ]
