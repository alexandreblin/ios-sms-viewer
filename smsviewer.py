from jinja2 import Environment, FileSystemLoader
import datetime
import os
import shutil
import sqlite3

OUTPUT_FOLDER = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__), 'output'))

jinja = Environment(loader=FileSystemLoader('templates'))


class MessagesDB:
    referenceTime = datetime.datetime(2001, 1, 1)
    currentDB = 'databases/3GS/'

    def __init__(self):
        self.conn = sqlite3.connect(os.path.join(MessagesDB.currentDB, 'sms.db'))
        self.conn.row_factory = sqlite3.Row

    def timestampToDate(self, timestamp):
        return MessagesDB.referenceTime + datetime.timedelta(seconds=timestamp)

    def getAllConversations(self):
        c = self.conn.cursor()

        res = c.execute('''
            select c.guid, group_concat(distinct h.id) as handles
            from chat c join chat_handle_join ch on c.ROWID=ch.chat_id join handle h on ch.handle_id=h.ROWID join chat_message_join cm on c.ROWID=cm.chat_id
            group by c.guid
        ''').fetchall()

        chats = []
        for row in res:
            chats.append({'guid': row['guid'], 'handles': row['handles']})

        return chats

    def getMessagesForGuid(self, guid):
        c = self.conn.cursor()

        res = c.execute('''
            select ROWID, id
            from handle
        ''').fetchall()

        handles = {}
        for row in res:
            handles[row['ROWID']] = row['id']

        res = c.execute('''
            select m.handle_id, m.text, m.service, m.date, m.is_from_me
            from message m join chat_message_join cm on m.ROWID=cm.message_id join chat c on c.ROWID=cm.chat_id
            where c.guid=?
        ''', (guid, )).fetchall()

        messages = []
        for row in res:
            messages.append({'handle': handles[row['handle_id']] if row['handle_id'] in handles else 0, 'text': row['text'], 'service': row['service'], 'date': self.timestampToDate(row['date']), 'is_from_me': row['is_from_me']})

        return sorted(messages, key=lambda k: k['date'])


if __name__ == '__main__':
    if os.path.exists(OUTPUT_FOLDER):
        shutil.rmtree(OUTPUT_FOLDER)

    os.makedirs(OUTPUT_FOLDER)

    db = MessagesDB()
    chats = db.getAllConversations()

    messages = {}
    for chat in chats:
        messages[chat['guid']] = db.getMessagesForGuid(chat['guid'])
        chat['msg_count'] = len(messages[chat['guid']])
        chat['last_msg'] = messages[chat['guid']][len(messages[chat['guid']])-1]

        jinja.get_template('conversation.html').stream(guid=chat['guid'], chat=chat, messages=messages[chat['guid']]).dump(os.path.join(OUTPUT_FOLDER, chat['guid']+'.html'), encoding='utf-8')

    chats = sorted(chats, key=lambda k: k['last_msg']['date'], reverse=True)

    jinja.get_template('index.html').stream(chats=chats).dump(os.path.join(OUTPUT_FOLDER, 'index.html'), encoding='utf-8')
