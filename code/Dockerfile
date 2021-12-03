FROM ubuntu
RUN apt-get update 			\
 && apt-get install -y iputils-ping 	\ 
 && apt-get install -y build-essential 	\
 && apt-get install -y python3 		\
 && apt-get install -y pip 		\
 && apt-get install -y vim
COPY ./requirements.txt ./requirements.txt
COPY ./third-party ./lib
COPY ./src ./lib/time-daemon
RUN pip install -r requirements.txt
WORKDIR ./lib/libfaketime/src
RUN make install
WORKDIR /
CMD ["/bin/bash"]

