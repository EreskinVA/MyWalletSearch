#---------------------------------------------------------------------
# Makefile for VanitySearch
#
# Author : Jean-Luc PONS

SRC_COMMON = Base58.cpp IntGroup.cpp main.cpp Random.cpp \
      Timer.cpp Int.cpp IntMod.cpp Point.cpp SECP256K1.cpp \
      Vanity.cpp GPU/GPUGenerate.cpp hash/ripemd160.cpp \
      hash/sha256.cpp hash/sha512.cpp Bech32.cpp Wildcard.cpp SegmentSearch.cpp \
      ProgressManager.cpp LoadBalancer.cpp AdaptivePriority.cpp KangarooSearch.cpp

SRC_X86 = hash/ripemd160_sse.cpp hash/sha256_sse.cpp AVX512.cpp AVX512BatchProcessor.cpp
SRC_ARM = NEON_ARM.cpp

OBJDIR = obj

ARCH := $(shell uname -m)

# Select sources based on architecture
ifeq ($(ARCH),arm64)
    SRC = $(SRC_COMMON) $(SRC_ARM)
else ifeq ($(ARCH),aarch64)
    SRC = $(SRC_COMMON) $(SRC_ARM)
else
    SRC = $(SRC_COMMON) $(SRC_X86)
endif

OBJET = $(addprefix $(OBJDIR)/, $(SRC:.cpp=.o))

ifdef gpu
OBJET += $(OBJDIR)/GPU/GPUEngine.o
endif

CXX        = g++
CUDA       = /usr/local/cuda-8.0
CXXCUDA    = /usr/bin/g++-4.8
NVCC       = $(CUDA)/bin/nvcc
# nvcc requires joint notation w/o dot, i.e. "5.2" -> "52"
ccap       = $(shell echo $(CCAP) | tr -d '.')

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

