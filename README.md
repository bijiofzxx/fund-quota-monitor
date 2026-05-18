# fund-quota-monitor
通过 天天基金网 监控基金单日最大申购限额并通知, 如 QDII 纳斯达克100 标普500等

## 一、配置config
  配置config/config.yaml python_interpreter/quota_threshold
  配置 email sender/password/receivers

## 二、初始换环境
  pip install -r requirements.txt

## 三、添加自选基金
  命令:python scripts/daily_search.py
  将根据config/config.yaml 中的关键词搜索并添加相关基金
  结果将写入 config/funds_master.json中

## 四、运行测试
  命令:python scripts/quota_monitor.py
  检查符合条件的自选基金并通知

## 五、启动计划任务
  命令:python run.py
  按照config/config.yaml check_quota 启动计划任务，并执行