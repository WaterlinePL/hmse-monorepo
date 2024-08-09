FROM ubuntu:22.04

# Setup env
RUN apt-get update
RUN apt-get install gfortran make -y

# Hydrus setup
COPY hydrus-1d-linux/src /src
RUN cd /src && make hydrus
RUN mv /src/hydrus /hydrus
RUN echo "/workspace" >> LEVEL_01.DIR

CMD ["./hydrus"]
