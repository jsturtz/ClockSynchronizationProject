FROM ubuntu
RUN apt-get update 			\
 && apt-get install -y iputils-ping 	\ 
 && apt-get install -y build-essential 	\
 && apt-get install -y python3 		\
 && apt-get install -y vim
COPY ./third-party ./lib
WORKDIR ./lib/libfaketime/src
RUN make install
WORKDIR ./
CMD ["/bin/bash"]

