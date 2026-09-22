from flask import Flask, request, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from datetime import datetime 
import bcrypt
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

db_cred = {
    "user": os.environ.get("DB_USER", "root"),
    "pass": os.environ.get("DB_PASSWORD", ""),
    "host": os.environ.get("DB_HOST", "localhost"),
    "name": os.environ.get("DB_NAME", "fantasy_league")
}

app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://\
{db_cred['user']}:{db_cred['pass']}@{db_cred['host']}/\
{db_cred['name']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
connection = engine.connect()


# Welcome Page
@app.route('/')
def welcome():
    return render_template('welcome.html')

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    # Get user from the database
    with db.engine.connect().execution_options(autocommit=True) as connection:
        query = text("SELECT * FROM User WHERE username = :username")
        result = connection.execute(
            query,
            {'username': username}
        ).fetchone()

    if not result:
        flash('Invalid username or password', 'error')
        return redirect(url_for('welcome'))

    hashed_password = result[4]

    # Verify hashed password
    try:
        if bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        ):
            flash(f'Welcome back, {username}!', 'success')
            session['user_id'] = result[0]
            session['username'] = result[1]

            leagues = fetch_leagues_for_user(result[0])
            return render_template('leagues.html', leagues=leagues)
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('welcome'))

    except (ValueError, TypeError):
        flash('Invalid username or password', 'error')
        return redirect(url_for('welcome'))

# Register Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['fullname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        try:
            with db.engine.connect() as connection:
                transaction = connection.begin()

                # Check if the username or email already exists
                check_query = text("""SELECT * FROM User WHERE Username = :username OR Email = :email""")
                result = connection.execute(check_query, {'username': username, 'email': email}).fetchone()

                # User already exists
                if result:
                    flash('Username or Email already exists', 'error')
                    transaction.rollback()  
                    return redirect(url_for('welcome'))

                # Call the signUp stored procedure
                sign_up_query = text(""" CALL signUp(:full_name, :email, :username, :password)""")
                connection.execute(sign_up_query, {'full_name': full_name,
                                                    'email': email,
                                                    'username': username,
                                                    'password': hashed_password})
                new_user(username, password, role)
                # Saving Changes to the database
                transaction.commit()
                flash('User registered successfully!', 'success')
                return redirect(url_for('welcome'))
        except Exception as e:
            transaction.rollback()
            flash(f'An error occurred while registering: {e}', 'error')
            return redirect(url_for('welcome'))

    return render_template('register.html')


# League Page - Displaying leagues for the user
@app.route('/leagues')
def display_leagues():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('welcome'))
    
    db.session.remove()

    user_id = int(session['user_id'])
    leagues = fetch_leagues_for_user(user_id)
    return render_template('leagues.html', leagues=leagues)

# Getting leagues for the user
def fetch_leagues_for_user(user_id):
    with db.engine.connect().execution_options(autocommit=True) as connection:
        query = text("""SELECT LeagueName, Commissioner, MaxTeams 
                 FROM League INNER JOIN User ON User.User_ID = League.Commissioner
                 WHERE League.Commissioner = :user_id UNION SELECT LeagueName, Commissioner, MaxTeams FROM User
                 INNER JOIN Team ON User.User_ID = Team.TeamOwner
                 INNER JOIN League ON Team.League_ID = League.League_ID
                 WHERE :user_id = Team.TeamOwner;""")
        result = connection.execute(query, {'user_id': user_id}).fetchall()

    return result

# Profile Page
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    try:
        user_id = int(session['user_id'])
    except:
        flash("Please sign in to view your profile.", "error")
        return redirect(url_for('welcome'))

    try:
        with db.engine.connect() as connection:
            transaction = connection.begin()
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                fullname = request.form['fullname']
                email = request.form['email']
                settings = request.form['settings']

                if not settings or settings.strip() == "":
                    settings = None

                hashed_password = None
                if password:
                    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                try:
                    if hashed_password:
                        query = text("""UPDATE User 
                                        SET FullName = :fullname, Email = :email, Username = :username, UserPassword = :password, ProfileSettings = :settings
                                        WHERE User_ID = :user_id""")
                        connection.execute(query, {'fullname': fullname,
                                                    'email': email,
                                                    'username': username,
                                                    'password': hashed_password,
                                                    'settings': settings,
                                                    'user_id': user_id})
                    else:
                        query = text("""UPDATE User 
                                    SET FullName = :fullname, Email = :email, Username = :username, ProfileSettings = :settings
                                    WHERE User_ID = :user_id """)
                        connection.execute(query, {'fullname': fullname,
                                                    'email': email,
                                                    'username': username,
                                                    'settings': settings,
                                                    'user_id': user_id})

                    transaction.commit()
                    flash("Profile updated successfully.", "success")
                except Exception as e:
                    transaction.rollback()
                    flash(f"An error occurred while updating the profile: {e}", "error")

            query = text("SELECT User_ID, FullName, Email, Username, ProfileSettings FROM User WHERE User_ID = :user_id")
            result = connection.execute(query, {'user_id': user_id}).fetchone()

            if result:
                user_details = {'User_ID': result[0],
                                'FullName': result[1],
                                'Email': result[2],
                                'Username': result[3],
                                'ProfileSettings': result[4]}
                
                return render_template('profile.html', user=user_details)
            else:
                flash("User not found.", "error")
                return redirect(url_for('welcome'))
    except Exception as e:
        flash(f"An error occurred: {e}", "error")
        return redirect(url_for('welcome'))


def get_teams_by_league(league_id):
    query = text("""SELECT * FROM Team INNER JOIN League ON League.League_ID = Team.League_ID WHERE :league_id = League.League_ID;""")
    return connection.execute(query, {'league_id': league_id}).fetchall()

def get_league_name(league_id):
    query = text("""SELECT LeagueName FROM League WHERE League_ID = :league_id""")
    return connection.execute(query, {'league_id': league_id}).fetchone()

# Teams Page
@app.route('/teams/<league_id>')
def teams(league_id):
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('welcome'))

    user_id = str(session['user_id'])
    teams_ = get_teams_by_league(league_id)
    leaguename = get_league_name(league_id)[0]
    return render_template('teams.html', teams=teams_, leagueName=leaguename, userid=user_id)

# CHANGED DECEMBER 2
def get_all_waivers():
    query = text("""SELECT Waiver.Waiver_ID, Team.TeamName, Player.FullName, 
    Waiver.WaiverStatus, Waiver.WaiverPickupDate, League.Commissioner 
    FROM Waiver INNER JOIN Team ON Waiver.Team_ID = Team.Team_ID 
    INNER JOIN Player ON Waiver.Player_ID = Player.Player_ID INNER JOIN
    League ON League.League_ID = Team.League_ID""")
    return connection.execute(query).fetchall()

# CHANGED DECEMBER 2
@app.route('/waivers', methods=['GET', 'POST'])
def waivers():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('welcome'))

    userid = str(session['user_id'])
    waivers = get_all_waivers()
    if request.method == 'POST':
        waiverid = request.form['approve']
        query = text("""UPDATE Waiver SET WaiverStatus='A' WHERE Waiver_ID = :waiverid """)
        result = connection.execute(query, {"waiverid": waiverid})
        connection.commit()
        waivers = get_all_waivers()
        flash('Waiver successfully approved! This page may take a moment to update buttons.', 'success')

    return render_template('waivers.html', waivers=waivers, userid=userid)

def get_team_player_set(user_id):
    # Returns a dictionary where the key is a team id
    # and the values are the players on that team
    query1 = text("""SELECT TeamName, Team_ID FROM Team WHERE Team.TeamOwner = :user_id""")
    results = connection.execute(query1, {'user_id': user_id}).fetchall()
    allTeams = {teamid: [] for teamid in results}

    query2 = text("""SELECT FullName, Player.Player_ID FROM Player INNER JOIN 
                    TeamToPlayer ON TeamToPlayer.Player_ID = Player.Player_ID WHERE 
                    TeamToPlayer.Team_ID = :teamid""")
    
    for teamid in allTeams:
        results = connection.execute(query2, {'teamid': teamid[1]}).fetchall()
        allTeams[teamid] = [playerid for playerid in results]
    return allTeams

# Creating new waiver page
@app.route('/waiver/new', methods=['GET', 'POST'])
def newWaiver():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('welcome'))

    user_id = int(session['user_id'])
    possible_waivers = get_team_player_set(user_id)

    if request.method == 'POST':
        player_id = request.form['playerid']

        new_waiver = text("""CALL newWaiver(:playerid)""")
        connection.execute(new_waiver, {'playerid': player_id})

        flash('Waiver successfully created!', 'success')
        return redirect(url_for('display_leagues'))
    # Returns team and playerid
    return render_template('new-waiver.html', waiverSet=possible_waivers)

# All the teams page
@app.route('/all-teams', methods=['GET', 'POST'])
def all_teams():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('welcome'))

    teams = db.session.execute(text('SELECT * FROM Team')).fetchall() 

    selected_team = None
    players = []

    if request.method == 'POST':
        selected_team_id = request.form.get('team_id')

        if selected_team_id:
            players = db.session.execute(text('''SELECT Player.Player_ID, Player.FullName, Player.Sport, Player.Position, Player.FantasyPoints
                                                FROM Player
                                                JOIN TeamToPlayer tp ON tp.Player_ID = Player.Player_ID
                                                WHERE tp.Team_ID = :team_id'''), {'team_id': selected_team_id}).fetchall()

            selected_team = db.session.execute(text('SELECT TeamName FROM Team WHERE Team_ID = :team_id'), {'team_id': selected_team_id}).fetchone()

    return render_template('all-teams.html', teams=teams, players=players, selected_team=selected_team)

# Displaying all the matches page
@app.route('/matches', methods=['GET', 'POST'])
def matches():
    if 'user_id' not in session:
        flash("Please log in to view your trades.", "error")
        return redirect(url_for('welcome'))
    
    userid = session.get('user_id')

    league_name = "Fantasy League" 
    teams = db.session.execute(text('SELECT * FROM Team WHERE League_ID = :league_id'), {'league_id': 1}).fetchall()

    selected_team = None
    players = []
    team_matches = []
    search_query = ""

    if request.method == 'POST':
        search_query = request.form.get('search_query')

        if search_query:
            teams = db.session.execute(text('SELECT * FROM Team WHERE TeamName LIKE :search_query AND League_ID = :league_id'),
                                        {'search_query': f'%{search_query}%', 'league_id': 1}).fetchall()

            if teams:
                selected_team_id = teams[0].Team_ID  

                team_matches = db.session.execute(
                    text('''SELECT Match_ID, Team1_ID, Team2_ID, MatchDate, FinalScore, t1.TeamName AS team1_name, t2.TeamName AS team2_name
                            FROM TeamMatch 
                            JOIN Team t1 ON Team1_ID = t1.Team_ID
                            JOIN Team t2 ON Team2_ID = t2.Team_ID
                            WHERE Team1_ID = :team_id OR Team2_ID = :team_id
                            ORDER BY MatchDate DESC'''), {'team_id': selected_team_id}).fetchall()

    return render_template('matches.html', teams=teams, players=players, selected_team=selected_team, team_matches=team_matches, 
                                           leagueName=league_name, userid=userid, search_query=search_query)


# Trades Page
@app.route('/trade', methods=['GET', 'POST'])
def proposed_trades():
    if 'user_id' not in session:
        flash("Please log in to view your trades.", "error")
        return redirect(url_for('welcome'))

    user_id = session['user_id']
    trades = []
    try:
        # Getting all the trades that are related to the user's team
       query = text(""" SELECT Trade.Trade_ID,
                        (SELECT TeamName FROM Team WHERE Team.Team_ID = Trade.Team1_ID) AS Team1_Name,
                        (SELECT TeamName FROM Team WHERE Team.Team_ID = Trade.Team2_ID) AS Team2_Name,
                        (SELECT FullName FROM Player WHERE Player.Player_ID = Trade.TradedPlayer1_ID) AS Player1_Name,
                        (SELECT FullName FROM Player WHERE Player.Player_ID = Trade.TradedPlayer2_ID) AS Player2_Name
                        FROM Trade
                        WHERE Trade.Team1_ID IN (SELECT Team_ID FROM Team WHERE Team.TeamOwner = :user_id)
                        OR Trade.Team2_ID IN (SELECT Team_ID FROM Team WHERE Team.TeamOwner = :user_id)""")
       trades = db.session.execute(query, {'user_id': user_id}).fetchall()
    except Exception as e:
        flash(f"An error occurred: {e}", "error")

    return render_template('trades.html', trades=trades)

# Propose Trade page - Gets all the leagues
@app.route('/propose-trade', methods=['GET', 'POST'])
def create_trade_team():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('welcome'))
    user_id = int(session['user_id'])
    leagues = fetch_leagues_for_user(user_id)
    return render_template('tradesb.html', leagues=leagues)

# Propose Trade - Gets all the teams in a selected league
@app.route('/trade-teams/<league_id>')
def choose_trade_team(league_id):
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('welcome'))

    user_id = str(session['user_id'])
    teams_ = get_teams_by_league(league_id)
    leaguename = get_league_name(league_id)[0]
    return render_template('trade-teams.html', teams=teams_, leagueName=leaguename, userid=user_id)

# Displayes all the players from the user's team and the selected team to complete the trade
@app.route('/trade-in-teams/<team_id>', methods=['GET', 'POST'])
def choose_trade_players(team_id):
    user_id = str(session['user_id'])
    user_teams = []
    other_teams = []
    
    if request.method == 'POST':
        user_player_id = request.form.get('user_player')
        other_player_id = request.form.get('other_player')
        if user_player_id and other_player_id:
            try:
                query_get_team = text("""SELECT DISTINCT Team.Team_ID
                                        FROM Team
                                        INNER JOIN User ON Team.TeamOwner = :user_id""")
                user_team_id_result = db.session.execute(query_get_team, {'user_id': user_id}).fetchone()

                user_team_id = user_team_id_result[0]  

                # Calling the newTrade stored procedure 
                query = text("""CALL newTrade(:team1_id, :team2_id, :traded_player1_id, :traded_player2_id, :trade_date, :trade_status)""")

                db.session.execute(query, {'team1_id': user_team_id,
                                            'team2_id': team_id,
                                            'traded_player1_id': user_player_id,
                                            'traded_player2_id': other_player_id,
                                            'trade_date': datetime.now().date(),
                                            'trade_status': 'P'})
                db.session.commit()

                flash(f"Trade proposed successfully.", "success")
                return redirect(url_for('proposed_trades'))  

            except Exception as e:
                db.session.rollback()
                flash(f"An error occurred while proposing the trade: {e}", "error")

    try:
        # Getting players from the user's team
        query = text("""SELECT DISTINCT Player.Player_ID, Player.FullName
                        FROM Player
                        INNER JOIN TeamToPlayer ON Player.Player_ID = TeamToPlayer.Player_ID 
                        INNER JOIN Team ON TeamToPlayer.Team_ID = Team.Team_ID
                        INNER JOIN User ON Team.TeamOwner = :user_id""")
                    
        user_teams = db.session.execute(query, {'user_id': user_id}).fetchall()

        # Getting players from the selected team
        query2 = text("""SELECT DISTINCT Player.Player_ID, Player.FullName
                        FROM Player 
                        INNER JOIN TeamToPlayer ON Player.Player_ID = TeamToPlayer.Player_ID 
                        INNER JOIN Team ON TeamToPlayer.Team_ID = Team.Team_ID
                        WHERE :team_id = Team.Team_ID""")
        
        other_teams = db.session.execute(query2, {'team_id': team_id}).fetchall()
    except Exception as e:
        flash(f"An error occurred: {e}", "error")

    return render_template('trade-players.html', user_teams=user_teams, other_teams=other_teams)


# Show all players of the other, previously selected team
def other_players_trade(teamid):
    return db.session.execute(text("""SELECT Player.Player_ID, FullName
                                    FROM Player 
                                    INNER JOIN TeamToPlayer ON Player.Player_ID = TeamToPlayer.Player_ID 
                                    INNER JOIN Team ON TeamToPlayer.Team_ID = Team.Team_ID
                                    WHERE :teamid = Team.Team_ID;"""), {"teamid": teamid}).fetchall()


def get_players_in_draft():
    query = text("""SELECT Player.Player_ID, FullName FROM Player WHERE FullName NOT IN
                    (SELECT FullName FROM Player INNER JOIN TeamToPlayer
                     ON Player.Player_ID = TeamToPlayer.Player_ID)""")
    return db.session.execute(query).fetchall()



def draft_is_open(teamid):
    query1 = text("""SELECT Team.League_ID FROM Team WHERE Team.Team_ID = :teamid""")
    leagueid = connection.execute(query1, {"teamid": teamid}).fetchone()[0]
    query2 = text("SELECT Draft.DraftStatus FROM Draft WHERE Draft.League_ID = :leagueid")
    value = connection.execute(query2, {"leagueid": leagueid}).fetchone()[0]
    # value should be I for incomplete or C for complete
    return (str(value).upper() == "I")


@app.route('/change-my-team/<teamid>', methods=['GET', 'POST'])
def change_the_team(teamid):
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('welcome'))
    
    try:
        players = other_players_trade(teamid)
        up_for_draft = get_players_in_draft()
        draftOpen = draft_is_open(teamid)

        if request.method == 'POST':
            if 'delete' in request.form:
                player_id = request.form['delete']
                try:
                    sql = text("DELETE FROM TeamToPlayer WHERE Player_ID = :playerid")
                    db.session.execute(sql, {"playerid": player_id})
                    db.session.commit()
                    flash(f'Player with ID {player_id} has been removed from the team.', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f"Error removing player: {e}", 'error')
            
            if 'draft' in request.form:
                player_id = request.form['draft']
                try:
                    sql = text("INSERT INTO TeamToPlayer VALUES (:teamid, :player_id)")
                    db.session.execute(sql, {"teamid": teamid, "player_id": player_id})
                    db.session.commit()
                    flash(f'Player with ID {player_id} has joined your team.', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f"Error adding player: {e}", 'error')

            # Refresh data after updates
            players = other_players_trade(teamid)
            up_for_draft = get_players_in_draft()

        return render_template(
            'player-changes.html',
            teamid=teamid,
            players=players,
            freeToDraft=up_for_draft,
            draftOpen=draftOpen
        )
    except Exception as e:
        flash(f"An error occurred: {e}", 'error')
        return redirect(url_for('teams'))



def get_all_users():
    query = text("""SELECT User.Username, User.User_ID FROM User""")
    return connection.execute(query)

def get_user_role():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return "unknown"

    user_id = session['user_id']

    try:
        query = text("SELECT Username FROM User WHERE User_ID = :user_id;")
        result = db.session.execute(query, {"user_id": user_id}).fetchone()

        if not result:
            flash('User not found. Please log in again.', 'error')
            return "unknown"

        username = result[0]  
        print(f"DEBUG: Fetched username for user_id {user_id}: '{username}'")  

        query = text(f"SHOW GRANTS FOR '{username}'@'localhost';")
        grants = db.session.execute(query).fetchall()
        for grant in grants:
            if "commissioner_role" in grant[0]:
                return "commissioner"
            elif "user_role" in grant[0]:
                return "user"
        return "unknown"
    except Exception as e:
        flash(f"Error retrieving user role: {e}", 'error')
        return "unknown"


@app.route('/newleague', methods=['GET', 'POST'])
def new_league():
    if 'user_id' not in session:
        flash('Please log in first', 'error')
        return redirect(url_for('welcome'))
    
    role = get_user_role()

    if role != 'commissioner':
        flash('Only commissioners can create a new league.', 'error')
        return redirect(url_for('display_leagues'))
    # CHECK PRIVILEGE SOMEHOW
    allUsers = get_all_users()

    with db.engine.connect().execution_options(autocommit=True) as connection:

        if request.method == 'POST':
            leaguename = request.form['leaguename']
            commissioner = request.form['commissioner']
            leaguetype = request.form['leaguetype']
            maxteams = request.form['maxteams']

            query = text("""CALL newLeague(:leaguename, :commissioner, :leaguetype, :maxteams);""")
            connection.execute(query, {"leaguename": leaguename, "commissioner": commissioner,
                                    "leaguetype": leaguetype, "maxteams": maxteams})
            
            flash(f'New League {leaguename} has been created.', 'success')
            connection.commit()
            return redirect(url_for("display_leagues"))

        return render_template('create-league.html', allUsers=allUsers)

# Log Out page
@app.route('/logout')
def logout():
    session.clear()  
    flash("You have been logged out.", "info")
    return redirect(url_for('welcome'))

# register new user and grant privileges
def new_user(new_username, password, role):
    try:
        create_user_query = text("""CREATE USER :new_username@'localhost' IDENTIFIED BY :password;""")
        db.session.execute(create_user_query, {"new_username": new_username, "password": password})

        if role == 'commissioner':
            grant_role_query = text("""GRANT commissioner_role TO :new_username@'localhost';""")
            db.session.execute(grant_role_query, {"new_username": new_username})

        else:
            grant_role_query = text(f"GRANT user_role TO '{new_username}'@'localhost';")
            db.session.execute(grant_role_query)

            #grant_privileges_query = text(f"""
                #GRANT SELECT ON fantasy_league.League TO '{new_username}'@'localhost';
                #GRANT SELECT ON fantasy_league.Team TO '{new_username}'@'localhost';
               # GRANT SELECT ON fantasy_league.Player TO '{new_username}'@'localhost';
            #""")
            #db.session.execute(grant_privileges_query)
        

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Failed to create user or assign role: {e}")


if __name__ == '__main__':
    app.run()
