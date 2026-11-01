#!/usr/bin/env bash
case "${1:-}" in
  *Username*) printf '%s\n' "${GIT_MIRROR_USERNAME:-oauth2}" ;;
  *Password*) printf '%s\n' "${TOKEN:?TOKEN 未设置}" ;;
  *) exit 1 ;;
esac
