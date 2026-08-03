# Chess For Dad — rules brain build.
#
# Builds `chess-for-dad`, the extracted OmegaZero move generator that serves as
# the single source of truth for move legality and game status. Kept portable
# (no -march=native) so the same source builds on macOS locally and on the
# Linux server that hosts the live game.

CXX      := g++
STD      := -std=c++17
WARN     := -Wall -Werror -Wextra -Wshadow
CXXFLAGS := $(STD) $(WARN) -O2

BIN      := chess-for-dad
SRCDIR   := src
BUILDDIR := build

# magics.cc is a huge generated lookup table; optimizing it is slow and
# pointless, so it is always compiled at -O0 (same policy as OmegaZero).
OBJS := $(BUILDDIR)/board.o $(BUILDDIR)/engine.o $(BUILDDIR)/masks.o \
        $(BUILDDIR)/main.o $(BUILDDIR)/magics.o

all: $(BIN)

$(BIN): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $@ $(OBJS)

$(BUILDDIR)/magics.o: $(SRCDIR)/magics.cc | $(BUILDDIR)
	$(CXX) $(STD) $(WARN) -O0 -c -o $@ $<

$(BUILDDIR)/%.o: $(SRCDIR)/%.cc | $(BUILDDIR)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

clean:
	rm -rf $(BUILDDIR) $(BIN)

.PHONY: all clean
