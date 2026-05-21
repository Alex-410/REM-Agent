import itchat

itchat.auto_login(hotReload=True)
itchat.send('测试消息', toUserName='filehelper')
print('消息已发送')
