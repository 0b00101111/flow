---
title: "{{ dateFormat "2006-01-02" .Date }} 第{{ dateFormat "2" .Date }}周 {{ dateFormat "Monday" .Date | replaceRE "Monday" "星期一" | replaceRE "Tuesday" "星期二" | replaceRE "Wednesday" "星期三" | replaceRE "Thursday" "星期四" | replaceRE "Friday" "星期五" | replaceRE "Saturday" "星期六" | replaceRE "Sunday" "星期日" }}日记"
date: {{ .Date }}
type: "daily"
---

## 今日记录
