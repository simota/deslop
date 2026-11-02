# deslop — install helpers
#
#   make link      symlink skills/deslop into every installed host's skills dir
#   make unlink    remove those symlinks
#   make status    show what is installed, per host
#   make test      run offline regression tests
#   make check     tests plus skill consistency checks
#   make detect    run the detector on TARGET
#   make serve     start the local landing page and live detector
#
# A host that is not installed is skipped and named. Narrowing is explicit:
#
#   make link AGENT=claude             # this host only
#   make link PROJECT=/path/to/repo    # that project's .claude/skills instead
#   make link SKILLS_DIR=/some/path    # one literal path; AGENT unused

NAME    := deslop
PYTHON  ?= python3
shell_quote = '$(subst ','"'"',$(1))'
define deslop_newline


endef
ifneq ($(findstring $(deslop_newline),$(CURDIR)$(MAKEFILE_LIST)),)
$(error newlines in checkout or Makefile paths are not supported)
endif
# Make's path functions split on spaces, including spaces in the checkout.
# Remove earlier filenames until the remaining suffix names the loaded file.
# A failed lookup must stop before an install target can create a bad link.
REPO    := $(shell makefile=$(call shell_quote,$(MAKEFILE_LIST)); \
	while [ ! -f "$$makefile" ]; do \
	  makefile_tail=$${makefile#* }; \
	  [ "$$makefile_tail" != "$$makefile" ] || exit 1; \
	  makefile=$$makefile_tail; \
	done; \
	CDPATH= cd -- "$$(dirname -- "$$makefile")" && pwd)
ifeq ($(REPO),)
$(error cannot resolve this Makefile's checkout directory)
endif
SKILL   := $(REPO)/skills/$(NAME)

AGENT   ?= claude codex agy
PROJECT ?=

CODEX_HOME ?= $(HOME)/.codex
AGY_HOME   ?= $(HOME)/.gemini/antigravity-cli

tgt_claude := $(call shell_quote,$(HOME)/.claude) $(call shell_quote,$(HOME)/.claude/skills)
tgt_codex  := $(call shell_quote,$(CODEX_HOME)) $(call shell_quote,$(CODEX_HOME)/skills)
tgt_agy    := $(call shell_quote,$(AGY_HOME)) $(call shell_quote,$(AGY_HOME)/skills)

ifneq ($(SKILLS_DIR),)
QTARGETS := $(call shell_quote,$(SKILLS_DIR)) $(call shell_quote,$(SKILLS_DIR))
WHERE    := SKILLS_DIR=$(SKILLS_DIR)
else ifneq ($(PROJECT),)
QTARGETS := $(call shell_quote,$(PROJECT)) $(call shell_quote,$(PROJECT)/.claude/skills)
WHERE    := PROJECT=$(PROJECT)
else
UNKNOWN := $(filter-out claude codex agy,$(AGENT))
ifneq ($(UNKNOWN),)
$(error unknown AGENT '$(UNKNOWN)' - use claude, codex or agy, or set SKILLS_DIR)
endif
QTARGETS := $(foreach a,$(sort $(AGENT)),$(tgt_$(a)))
WHERE    := $(AGENT)
endif

QREPO   := $(call shell_quote,$(REPO))
QSKILL  := $(call shell_quote,$(SKILL))
QNAME   := $(call shell_quote,$(NAME))
QWHERE  := $(call shell_quote,$(WHERE))
QTARGET := $(call shell_quote,$(TARGET))

.PHONY: help link unlink status test check detect serve

help: ## list targets
	@grep -E '^[a-z-]+:.*## ' $(QREPO)/Makefile | awk -F':.*## ' '{printf "  %-8s %s\n", $$1, $$2}'

link: ## symlink the skill into every installed host's skills dir
	@n=0; skill=$(QSKILL); name=$(QNAME); where=$(QWHERE); \
	set -- $(QTARGETS); while [ $$# -gt 0 ]; do \
	  guard=$$1; dir=$$2; shift 2; d="$$dir/$$name"; \
	  if [ ! -d "$$guard" ]; then printf 'skip     %s - %s does not exist\n' "$$d" "$$guard"; continue; fi; \
	  if [ -L "$$d" ]; then \
	    if [ "$$(readlink -- "$$d")" = "$$skill" ]; then printf 'ok       %s already linked\n' "$$d"; n=$$((n+1)); continue; fi; \
	    printf 'refusing %s is a symlink to %s - resolve it, then re-run\n' "$$d" "$$(readlink -- "$$d")" >&2; exit 1; \
	  elif [ -e "$$d" ]; then \
	    printf 'refusing %s exists and is not a symlink - move it aside first\n' "$$d" >&2; exit 1; \
	  fi; \
	  mkdir -p -- "$$dir" && ln -s -- "$$skill" "$$d" || exit 1; \
	  printf 'linked   %s -> %s\n' "$$d" "$$skill"; n=$$((n+1)); \
	done; \
	if [ $$n -eq 0 ]; then printf 'nothing linked - no skills directory found for: %s\n' "$$where" >&2; exit 1; fi

unlink: ## remove the symlinks this Makefile created
	@skill=$(QSKILL); name=$(QNAME); set -- $(QTARGETS); while [ $$# -gt 0 ]; do \
	  dir=$$2; shift 2; d="$$dir/$$name"; \
	  if [ -L "$$d" ]; then \
	    if [ "$$(readlink -- "$$d")" = "$$skill" ]; then rm -f -- "$$d" || exit 1; printf 'unlinked %s\n' "$$d"; \
	    else printf 'left     %s - points at %s, not this repo\n' "$$d" "$$(readlink -- "$$d")"; fi; \
	  elif [ -e "$$d" ]; then printf 'left     %s - not a symlink\n' "$$d"; \
	  else printf 'absent   %s\n' "$$d"; fi; \
	done

status: ## show what is installed, per host
	@name=$(QNAME); set -- $(QTARGETS); while [ $$# -gt 0 ]; do \
	  guard=$$1; dir=$$2; shift 2; d="$$dir/$$name"; \
	  if [ ! -d "$$guard" ]; then printf 'skip     %s - host not installed\n' "$$d"; \
	  elif [ -L "$$d" ]; then printf 'symlink  %s -> %s\n' "$$d" "$$(readlink -- "$$d")"; \
	  elif [ -e "$$d" ]; then printf 'present  %s - not a symlink\n' "$$d"; \
	  else printf 'absent   %s\n' "$$d"; fi; \
	done

test: ## run offline regression tests
	@cd $(QREPO) && PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v

check: test ## tests plus skill consistency checks
	@skill=$(QSKILL); name=$(QNAME); fail=0; \
	sed -n '2,8p' "$$skill/SKILL.md" | grep -qxF -- "name: $$name" || { echo "MISS SKILL.md has no 'name: $$name'" >&2; fail=1; }; \
	d=$$(sed -n 's/^description: //p' "$$skill/SKILL.md" | head -1 | wc -c); \
	[ "$$d" -le 400 ] || { echo "MISS description is $$d chars; keep it under 400" >&2; fail=1; }; \
	[ $$fail -eq 0 ] && echo "check ok"; exit $$fail

detect: ## run the detector on TARGET
	@target=$(QTARGET); [ -n "$$target" ] || { echo "usage: make detect TARGET=path" >&2; exit 2; }; \
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(QSKILL)/scripts/detect.py -- "$$target"

serve: ## start local landing page and live detector server
	@PYTHONDONTWRITEBYTECODE=1 $(PYTHON) $(QREPO)/site/serve.py
