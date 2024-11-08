from datetime import datetime
import os,discord,sqlite3,time
from tracemalloc import start
from multiprocessing import Process, connection
from discord.ext import commands
from lib.logging import logServer,socketLogger
from config import LOG_PATH,DATABASE_PATH
from lib.utils import ensurePath,getRoles,natural_keys,get_started_user_assignments,get_user_points
from lib.exceptions import *

def main():
    ensurePath((LOG_PATH,DATABASE_PATH))
    log_server = Process(target=logServer)
    log_server.name = 'Logging Server'
    log_server.start()

    logger = socketLogger(__name__)

    TOKEN = 'OTXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'

    bot = commands.Bot(command_prefix='.')

    @bot.event
    async def on_ready():
        print(f'{bot.user.name} connected')

    @bot.event
    async def on_error(event, *args, **kwargs):
        ''

###########################################################
#
#
#   Assignment commands
#
#
###########################################################
    @bot.command(name='addAssignmentGroup')
    @commands.has_any_role(*getRoles(accessLevel=0))
    async def addAssignmentGroup(ctx,name,points,description):
        try:
            connection = sqlite3.connect(database=os.path.join(DATABASE_PATH,'assignments.db'),timeout=.5)
            cursor = connection.cursor()
            with connection:
                    cursor.execute(f'CREATE TABLE IF NOT EXISTS groups(name TEXT PRIMARY KEY, points INT,description TEXT);')
                    cursor.execute(f"CREATE TABLE IF NOT EXISTS {name}(name TEXT PRIMARY KEY, assignee TEXT, started TEXT, complete BIT, points INT);")
                    cursor.execute(f'INSERT INTO groups(name,points,description) VALUES("{name}","{points}","{description}");')
            await ctx.send(f'Added assignment group {name}')
        except Exception as e:
            logger.exception('Failed adding group')
            await ctx.send('Exception occured. Traceback: \n'+str(type(e).__name__)+': '+str(e))

    @bot.command(name='addAssignments', help='''
        adds assignments to group with name "(name)(id)"\n
        time_to_complete in seconds''')
    @commands.has_any_role(*getRoles(accessLevel=0))
    async def addAssignments(ctx,group,name,start_id:int,end_id:int):
        try:
            if start_id > end_id:
                raise ShittyInputError('Go fuck yourself')
            connection = sqlite3.connect(database=os.path.join(DATABASE_PATH,'assignments.db'),timeout=.5)
            cursor = connection.cursor()
            with connection:
                for id in range(start_id,end_id+1):
                    cursor.execute(f"""
                        INSERT INTO {group}(name)
                        VALUES('{name}{id}');""")
            await ctx.send(f'Added assignments to group "{group}"')
        except Exception as e:
            logger.exception('Failed adding assignments')
            await ctx.send('Exception occured. Traceback: \n'+str(type(e).__name__)+': '+str(e))

    @bot.command(name='deleteAssignmentGroup')
    @commands.has_any_role(*getRoles(accessLevel=0))
    async def DeleteAssignmentGroup(ctx,group):
        try:
            connection = sqlite3.connect(database=os.path.join(DATABASE_PATH,'assignments.db'),timeout=.5)
            cursor = connection.cursor()
            with connection:
                cursor.execute(f"DELETE FROM groups WHERE name = '{group}'")
                cursor.execute(f'DROP TABLE {group}')
            await ctx.send(f'Dropped assignment group "{group}"')
        except Exception as e:
            logger.exception('Failed deleting assignment group')
            await ctx.send('Exception occured. Traceback: \n'+str(type(e).__name__)+': '+str(e))

    @bot.command(name='listAssignmentGroups',help="Lists types of assignments you can apply for") #need to create another db to track groups
    @commands.has_any_role(*getRoles(accessLevel=3))
    async def listAssignmentGroups(ctx):
        try:
            connection = sqlite3.connect(database=os.path.join(DATABASE_PATH,'assignments.db'),timeout=.5)
            cursor = connection.cursor()
            with connection:
                cursor.execute(f"SELECT name, points, description FROM groups;")
            await ctx.send('Assignment Groups (groupname, points, description): \n'+'\n'.join([str(item) for item in cursor.fetchall()]))
        except Exception as e:
            logger.exception('Failed fetching assignment groups')
            await ctx.send('Exception occured. Traceback: \n'+str(type(e).__name__)+': '+str(e))

    @bot.command(name='getAssignment',help='getAssignment (assignmentGroup)') #need to create another db to track groups
    @commands.has_any_role(*getRoles(accessLevel=3))
    async def getAssignment(ctx, group):
        try:
            if len(assignments := get_started_user_assignments(ctx=ctx)) >= 12:
                await ctx.send('Already have max incomplete assignments. Assignments: \n'+'\n'.join(assignments))
            else:
                connection = sqlite3.connect(database=os.path.join(DATABASE_PATH,'assignments.db'),timeout=.5)
                cursor = connection.cursor()
                with connection:
                    cursor.execute(f"SELECT name FROM {group} WHERE assignee IS NULL;")
                assignments = [item[0] for item in cursor.fetchall()]
                assignments.sort(key=natural_keys)
                if assignments.__len__() == 0:
                    await ctx.send('no assignments open in this group')
                else:
                    assignment = assignments[0]
                    with connection:
                        cursor.execute(f'UPDATE {group} SET assignee = "{ctx.message.author.id}", started = "{int(time.time())}" WHERE name = "{assignment}"')
                    await ctx.send(f'Assigned to {assignment}')
        except Exception as e:
            logger.exception('Failed fetching assignment')
            await ctx.send('Exception occured. Traceback: \n'+str(type(e).__name__)+': '+str(e))

    @bot.command(name='dropAssignment',help='dropAssignment (assignmentGroup) (assignment)') #need to create another db to track groups
    @commands.has_any_role(*getRoles(accessLevel=3))
    async def dropAssignment(ctx,group,name):
        try:
            connection = sqlite3.connect(database=os.path.join(DATABASE_PATH,'assignments.db'),timeout=.5)
            cursor = connection.cursor()
            with connection:
                cursor.execute(f"UPDATE {group} SET assignee = NULL, started = NULL WHERE assignee = '{ctx.message.author.id}' AND name = '{name}';")
            await ctx.send('Dropped assignment (if valid)')
        except Exception as e:
            logger.exception('Failed dropping assignment')
            await ctx.send('Exception occured. Traceback: \n'+str(type(e).__name__)+': '+str(e))

    @bot.command(name='showAssignments',help="Shows your unfinished assignments") #need to create another db to track groups
    @commands.has_any_role(*getRoles(accessLevel=3))
    async def showAssignments(ctx):
        try:
            await ctx.send('Your unfinished assignments: \n'+'\n'.join(get_started_user_assignments(ctx)))
        except Exception as e:
            logger.exception('Failed requesting assignments')
            await ctx.send('Exception occured. Traceback: \n'+str(type(e).__name__)+': '+str(e))

    @bot.command(name='completeAssignment') #need to create another db to track groups
    @commands.has_any_role(*getRoles(accessLevel=2))
    async def completeAssignment(ctx,group,name):
        try:
            connection = sqlite3.connect(database=os.path.join(DATABASE_PATH,'assignments.db'),timeout=.5)
            cursor = connection.cursor()
            with connection:
                cursor.execute(f'SELECT points FROM groups WHERE name = "{group}"')
                points = cursor.fetchall()[0][0]
                cursor.execute(f"UPDATE {group} SET complete = 1, points = {points} WHERE name = '{name}';")
            await ctx.send(f'Marked assignment as complete for {points} points (if valid)')
        except Exception as e:
            logger.exception('Failed marking assignment as complete')
            await ctx.send('Exception occured. Traceback: \n'+str(type(e).__name__)+': '+str(e))

    @bot.command(name='assignmentPoints',help="Shows your total assignment points") #need to create another db to track groups
    @commands.has_any_role(*getRoles(accessLevel=3))
    async def assignmentPoints(ctx):
        try:
            await ctx.send('Total points: '+str(get_user_points(ctx)))
        except Exception as e:
            logger.exception('Failed requesting points')
            await ctx.send('Exception occured. Traceback: \n'+str(type(e).__name__)+': '+str(e))


    bot.run(TOKEN)

if __name__ == "__main__":
    main()
