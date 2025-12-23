#---------------------------------------------------------------------
# Makefile for VanitySearch
#
# Author : Jean-Luc PONS

SRC = Base58.cpp IntGroup.cpp main.cpp Random.cpp \
      Timer.cpp Int.cpp IntMod.cpp Point.cpp SECP256K1.cpp \
      Vanity.cpp GPU/GPUGenerate.cpp hash/ripemd160.cpp \
      hash/sha256.cpp hash/sha512.cpp hash/ripemd160_sse.cpp \
      hash/sha256_sse.cpp Bech32.cpp Wildcard.cpp SegmentSearch.cpp \
      ProgressManager.cpp LoadBalancer.cpp AdaptivePriority.cpp KangarooSearch.cpp \
      AVX512.cpp AVX512BatchProcessor.cpp NEON_ARM.cpp

OBJDIR = obj

ifdef gpu

OBJET = $(addprefix $(OBJDIR)/, \
        Base58.o IntGroup.o main.o Random.o Timer.o Int.o \
        IntMod.o Point.o SECP256K1.o Vanity.o GPU/GPUGenerate.o \
        hash/ripemd160.o hash/sha256.o hash/sha512.o \
        hash/ripemd160_sse.o hash/sha256_sse.o \
        GPU/GPUEngine.o Bech32.o Wildcard.o SegmentSearch.o \
        ProgressManager.o LoadBalancer.o AdaptivePriority.o KangarooSearch.o \
        AVX512.o AVX512BatchProcessor.o NEON_ARM.o)

else

OBJET = $(addprefix $(OBJDIR)/, \
        Base58.o IntGroup.o main.o Random.o Timer.o Int.o \
        IntMod.o Point.o SECP256K1.o Vanity.o GPU/GPUGenerate.o \
        hash/ripemd160.o hash/sha256.o hash/sha512.o \
        hash/ripemd160_sse.o hash/sha256_sse.o Bech32.o Wildcard.o \
        SegmentSearch.o ProgressManager.o LoadBalancer.o AdaptivePriority.o \
        KangarooSearch.o AVX512.o AVX512BatchProcessor.o NEON_ARM.o)

endif

CXX        = g++
CUDA       = /usr/local/cuda-8.0
CXXCUDA    = /usr/bin/g++-4.8
NVCC       = $(CUDA)/bin/nvcc
# nvcc requires joint notation w/o dot, i.e. "5.2" -> "52"
ccap       = $(shell echo $(CCAP) | tr -d '.')

# Определение архитектуры
ARCH := $(shell uname -m)

# Флаги для разных архитектур
ifeq ($(ARCH),arm64)
    # ARM (Apple Silicon M1/M2/M3)
    ARCHFLAGS = -march=armv8-a+crypto+simd
else ifeq ($(ARCH),aarch64)
    # ARM64 (Linux)
    ARCHFLAGS = -march=armv8-a+crypto+simd
else
    # x86_64 (Intel/AMD)
    ARCHFLAGS = -m64 -mssse3
endif

ifdef gpu
ifdef debug
CXXFLAGS   = -DWITHGPU $(ARCHFLAGS) -Wno-write-strings -g -I. -I$(CUDA)/include
else
CXXFLAGS   =  -DWITHGPU $(ARCHFLAGS) -Wno-write-strings -O3 -I. -I$(CUDA)/include
endif
LFLAGS     = -lpthread -L$(CUDA)/lib64 -lcudart
else
ifdef debug
CXXFLAGS   = $(ARCHFLAGS) -Wno-write-strings -g -I. -I$(CUDA)/include
else
CXXFLAGS   =  $(ARCHFLAGS) -Wno-write-strings -O3 -I. -I$(CUDA)/include
endif
LFLAGS     = -lpthread
endif


#--------------------------------------------------------------------

ifdef gpu
ifdef debug
$(OBJDIR)/GPU/GPUEngine.o: GPU/GPUEngine.cu
	$(NVCC) -G -maxrregcount=0 --ptxas-options=-v --compile --compiler-options -fPIC -ccbin $(CXXCUDA) -m64 -g -I$(CUDA)/include -gencode=arch=compute_$(ccap),code=sm_$(ccap) -o $(OBJDIR)/GPU/GPUEngine.o -c GPU/GPUEngine.cu
else
$(OBJDIR)/GPU/GPUEngine.o: GPU/GPUEngine.cu
	$(NVCC) -maxrregcount=0 --ptxas-options=-v --compile --compiler-options -fPIC -ccbin $(CXXCUDA) -m64 -O2 -I$(CUDA)/include -gencode=arch=compute_$(ccap),code=sm_$(ccap) -o $(OBJDIR)/GPU/GPUEngine.o -c GPU/GPUEngine.cu
endif
endif

$(OBJDIR)/%.o : %.cpp
	$(CXX) $(CXXFLAGS) -o $@ -c $<

all: VanitySearch

VanitySearch: $(OBJET)
	@echo Making VanitySearch...
	$(CXX) $(OBJET) $(LFLAGS) -o VanitySearch

$(OBJET): | $(OBJDIR) $(OBJDIR)/GPU $(OBJDIR)/hash

$(OBJDIR):
	mkdir -p $(OBJDIR)

$(OBJDIR)/GPU: $(OBJDIR)
	cd $(OBJDIR) &&	mkdir -p GPU

$(OBJDIR)/hash: $(OBJDIR)
	cd $(OBJDIR) &&	mkdir -p hash

clean:
	@echo Cleaning...
	@rm -f obj/*.o
	@rm -f obj/GPU/*.o
	@rm -f obj/hash/*.o

