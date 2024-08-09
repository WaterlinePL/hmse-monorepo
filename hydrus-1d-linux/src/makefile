# undone
# raw command for compile 
# gfortran HYDRUS.FOR  HYSTER.FOR  INPUT.FOR  MATERIAL.FOR  OUTPUT.FOR  SINK.FOR  SOLUTE.FOR  TEMPER.FOR  TIME.FOR WATFLOW.FOR -o hydrus
# use some makefile variables

# UNAME_S := $(shell uname -s)
CC = gfortran

objects = HYDRUS.o  HYSTER.o  INPUT.o  MATERIAL.o  OUTPUT.o  SINK.o  SOLUTE.o  TEMPER.o  TIME.o  WATFLOW.o METEO.o
FFLAGS =

hydrus: $(objects)
	$(CC) -o hydrus $(objects)
%.o : %.FOR
	$(CC) $(FFLAGS) -c $< 


clean : 
	rm $(objects)
