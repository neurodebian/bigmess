BUILDDIR=$(CURDIR)/build
MAN_DIR=$(BUILDDIR)/man

PYTHON = python
PYTHON3 = python3
NOSETESTS = $(PYTHON) $(shell which nosetests)

# Setup local PYTHONPATH depending on the version of provided $(PYTHON)
PYVER = $(shell $(PYTHON) -c 'import sys; print(sys.version_info[0])')
ifeq ($(PYVER),2)
 # just use the local sources and run tests 'in source'
 TEST_DIR = .
 LPYTHONPATH = .:$(PYTHONPATH)
else
 # for 3 (and hopefully not above ;) ) -- corresponding build/
 # since sources go through 2to3 conversion
 TEST_DIR = $(BUILD3DIR)
 LPYTHONPATH = $(BUILD3DIR):$(PYTHONPATH)
endif

htmldoc:
	PYTHONPATH=..:$(LPYTHONPATH) sphinx-autogen \
			   -t doc/templates \
			   -o doc/source/generated doc/source/*.rst
	PYTHONPATH=..:$(LPYTHONPATH) $(MAKE) -C doc html BUILDDIR=$(BUILDDIR)

clean:
	rm -rf build
	rm -f MANIFEST
	rm -rf doc/source/generated

manpages: mkdir-MAN_DIR
	@echo "I: Creating manpages"
	PYTHONPATH=$(LPYTHONPATH) help2man --no-discard-stderr \
		--help-option="--help-np" -N -n "command line interface for bigmess" \
			bin/bigmess > $(MAN_DIR)/bigmess.1
	for cmd in $$(grep import < bigmess/cmdline/__init__.py | cut -d _ -f 2-); do \
		summary="$$(grep 'man: -*-' < bigmess/cmdline/cmd_$${cmd}.py | cut -d '%' -f 2-)"; \
		PYTHONPATH=$(LPYTHONPATH) help2man --no-discard-stderr \
			--help-option="--help-np" -N -n "$$summary" \
				"bin/bigmess $${cmd}" > $(MAN_DIR)/bigmess-$${cmd}.1 ; \
	done

test:
	PYTHONPATH=$(LPYTHONPATH) $(NOSETESTS) \
		--nocapture \
		--exclude='external.*' \
		--with-doctest \
		--doctest-extension .rst \
		--doctest-tests doc/source/*.rst \
		.

release-%:
	@echo "Testing for uncommited changes"
	@git diff --quiet HEAD
	sed -i -e 's/^__version__ = .*$$/__version__ = "$(*)"/' bigmess/__init__.py
	git add bigmess/__init__.py
	@echo "Create and tag release commit"
	git commit -m "Release $(*)"
	git tag -s -a -m "Release $(*)" release/$(*)
	sed -i -e 's/^__version__ = .*$$/__version__ = "$(*)+dev"/' bigmess/__init__.py
	git add bigmess/__init__.py
	git commit -m "Increment version for new development cycle"



#
# Little helpers
#

mkdir-%:
	if [ ! -d $($*) ]; then mkdir -p $($*); fi

.PHONY: htmldoc clean manpages
