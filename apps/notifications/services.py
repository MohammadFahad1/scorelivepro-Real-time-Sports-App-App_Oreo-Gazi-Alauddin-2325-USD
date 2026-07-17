import os
import firebase_admin
from firebase_admin import messaging, credentials
from django.conf import settings
from .models import NotificationLog

class NotificationService:
    @staticmethod
    def ensure_firebase_initialized():
        """
        Lazily initialize Firebase Admin SDK.
        Ensures Celery workers never fail silently if apps.py couldn't initialize.
        """
        if not firebase_admin._apps:
            try:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                firebase_admin.initialize_app(cred)
                print("Firebase Admin lazily initialized in NotificationService.")
            except Exception as e:
                print(f"CRITICAL: Failed to initialize Firebase in NotificationService: {e}")
                # Log if the file is a directory (Docker volume common issue) or missing
                if not os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                    print("ERROR: firebase-credentials.json is COMPLETELY MISSING!")
                elif os.path.isdir(settings.FIREBASE_CREDENTIALS_PATH):
                    print("ERROR: firebase-credentials.json is a DIRECTORY, not a file!")
                else:
                    try:
                        with open(settings.FIREBASE_CREDENTIALS_PATH, 'r') as f:
                            content = f.read()
                            print(f"\n{'='*60}")
                            print(f"📄 FIREBASE JSON CONTENTS MOUNTED IN DOCKER:")
                            print(content)
                            print(f"{'='*60}\n")
                    except Exception as read_err:
                        print(f"Could not read the file for debugging: {read_err}")
    @staticmethod
    def send_push_to_topic(topic, title, body, data=None, event_type='CUSTOM'):
        """
        Sends a message to a topic and logs it with the specific event type.
        If firebase credentials are missing, falls back to a simulated sent state for dev/testing.
        """
        # Ensure data is dict
        if data is None: data = {}
        
        # Check if we should use Simulated Dev Mode
        use_simulator = not os.path.exists(settings.FIREBASE_CREDENTIALS_PATH)
        
        if use_simulator:
            print(f"\n{'='*60}")
            print(f"⚠️  SIMULATOR MODE: FIREBASE CREDENTIALS FILE MISSING")
            print(f"   Simulating Push to Topic: {topic}")
            print(f"   Title: {title}")
            print(f"   Body: {body}")
            print(f"   Data: {data}")
            print(f"{'='*60}\n")
            
            # Log to DB as SENT so local inbox lists are fully testable
            try:
                NotificationLog.objects.create(
                    topic=topic,
                    title=title,
                    body=body,
                    status='SENT',
                    event_type=event_type,
                    error_message="[SIMULATED] Firebase credentials missing, simulated successfully.",
                    data=data
                )
            except Exception as e:
                print(f"Database logging failed: {e}")
            return True

        # Otherwise, proceed with actual Firebase sending
        NotificationService.ensure_firebase_initialized()
        
        status = 'SENT'
        error_msg = None
        try:
            # Firebase only accepts strings in data map
            formatted_data = {k: str(v) for k, v in data.items()}
            
            print(f"\n{'='*60}")
            print(f"🚀 PUSHING TO FIREBASE TOPIC: {topic}")
            print(f"   Title: {title}")
            print(f"   Body: {body}")
            print(f"   Data: {formatted_data}")
            print(f"{'='*60}\n")
            
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=formatted_data,
                topic=topic,
            )
            response = messaging.send(message=message)
            error_msg = str(response) # Save Firebase Message ID to DB
            
            print(f"\n{'='*60}")
            print(f"✅ SUCCESS! FIREBASE ACCEPTED NOTIFICATION")
            print(f"   Message ID: {response}")
            print(f"   Topic: {topic}")
            print(f"{'='*60}\n")
        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            print(f"Push Error ({topic}): {e}")
            
            # --- USER DEMAND: PROOF OF JSON FILE ---
            try:
                with open(settings.FIREBASE_CREDENTIALS_PATH, 'r') as f:
                    print(f"\n{'='*60}")
                    print(f"📄 FIREBASE JSON FILE AS SEEN BY DOCKER (Proof):")
                    print(f.read())
                    print(f"{'='*60}\n")
            except Exception as read_err:
                print(f"Could not read the file for debugging: {read_err}")
        
        # Log to DB
        try:
            NotificationLog.objects.create(
                topic=topic,
                title=title,
                body=body,
                status=status,
                event_type=event_type,
                error_message=error_msg,
                data=data
            )
        except Exception:
            pass
        return status == 'SENT'
    
    @staticmethod
    def send_push_to_token(token, title, body, data=None):
        """
        TEMPORARY: Sends a message directly to a specific device FCM token for testing.
        If firebase credentials are missing, falls back to simulated sent state for dev/testing.
        """
        if data is None: data = {}
        
        use_simulator = not os.path.exists(settings.FIREBASE_CREDENTIALS_PATH)
        
        if use_simulator:
            print(f"\n{'='*60}")
            print(f"⚠️  SIMULATOR MODE: FIREBASE CREDENTIALS FILE MISSING")
            print(f"   Simulating Push to Token: {token[:20]}...")
            print(f"   Title: {title}")
            print(f"   Body: {body}")
            print(f"   Data: {data}")
            print(f"{'='*60}\n")
            
            topic_display = "test_token (Simulated Device)"
            try:
                from .models import UserDevice
                device = UserDevice.objects.filter(registration_id=token).first()
                if device and device.user:
                    topic_display = f"テスト (Simulated): {device.user.email}"
            except:
                pass
                
            try:
                NotificationLog.objects.create(
                    topic=topic_display,
                    title=title,
                    body=body,
                    status='SENT',
                    event_type='DEV_TEST',
                    error_message="[SIMULATED] Firebase credentials missing, simulated successfully.",
                    data=data
                )
            except Exception as e:
                print(f"Database logging failed: {e}")
                
            return {"success": True, "message_id": "simulated-msg-id-12345", "simulated": True}

        # Otherwise proceed with actual Firebase sending
        NotificationService.ensure_firebase_initialized()
        formatted_data = {k: str(v) for k, v in data.items()}
        
        print(f"\n{'='*60}")
        print(f"🚀 PUSHING TO FIREBASE TOKEN: {token[:20]}...")
        print(f"   Title: {title}")
        print(f"   Body: {body}")
        print(f"{'='*60}\n")
        
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=formatted_data,
            token=token,
        )
        try:
            response = messaging.send(message=message)
            print(f"✅ SUCCESS! FIREBASE ACCEPTED TOKEN NOTIFICATION: {response}")
            # Lookup the specific user email for this token, to make the logs incredibly clear
            topic_display = "test_token (Unknown Device)"
            try:
                from .models import UserDevice
                device = UserDevice.objects.filter(registration_id=token).first()
                if device and device.user:
                    topic_display = f"テスト (Test): {device.user.email}"
            except:
                pass
            
            try:
                NotificationLog.objects.create(
                    topic=topic_display,
                    title=title,
                    body=body,
                    status='SENT',
                    event_type='DEV_TEST',
                    error_message=str(response),
                    data=data
                )
            except Exception:
                pass
                
            return {"success": True, "message_id": response}
        except Exception as e:
            print(f"❌ Failed to send to token: {e}")
            
            topic_display = "test_token (Unknown Device)"
            try:
                from .models import UserDevice
                device = UserDevice.objects.filter(registration_id=token).first()
                if device and device.user:
                    topic_display = f"テスト (Test): {device.user.email}"
            except:
                pass

            try:
                NotificationLog.objects.create(
                    topic=topic_display,
                    title=title,
                    body=body,
                    status='FAILED',
                    event_type='DEV_TEST',
                    error_message=str(e),
                    data=data
                )
            except Exception:
                pass
                
            try:
                with open(settings.FIREBASE_CREDENTIALS_PATH, 'r') as f:
                    pass # Silenced to not clutter logs anymore
            except Exception:
                pass
            return {"success": False, "error": str(e)}

    @staticmethod
    def send_goal_alert(scoring_team_name, home_team_name, away_team_name, score, home_team_id, away_team_id, match_id, league_id=None):
        """
        Sends goal alerts to Team Topics, Match Topic, and optionally League Topic.
        """
        title = f"⚽ Goal by {scoring_team_name}!"
        body = f"Current Score: {home_team_name} {score} {away_team_name}"
        
        # 1. Send to Home Team Fans
        data_home = {
            "type": "GOAL", 
            "match_id": str(match_id), 
            "team_id": str(home_team_id),
            "score": str(score),
            "reason": f"Following {home_team_name}"
        }
        NotificationService.send_push_to_topic(f"team_{home_team_id}", title, body, data_home, event_type='GOAL')
        
        # 2. Send to Away Team Fans
        data_away = {
            "type": "GOAL", 
            "match_id": str(match_id), 
            "team_id": str(away_team_id),
            "score": str(score),
            "reason": f"Following {away_team_name}"
        }
        NotificationService.send_push_to_topic(f"team_{away_team_id}", title, body, data_away, event_type='GOAL')
        
        # 3. Send to Match Followers
        data_match = data_home.copy()
        data_match["reason"] = f"Saved Match"
        NotificationService.send_push_to_topic(f"match_{match_id}", title, body, data_match, event_type='GOAL')

        # 4. Send to League Followers (if provided)
        if league_id:
            data_league = data_home.copy()
            data_league["reason"] = "Following League"
            NotificationService.send_push_to_topic(f"league_{league_id}", title, body, data_league, event_type='GOAL')

    @staticmethod
    def send_match_result_alert(home_team, away_team, score, match_id, league_id):
        """
        Sends Full Time results to BOTH teams, the Match Topic, AND the League Topic.
        """
        title = "🏁 Full Time"
        body = f"Final Result: {home_team.name} {score} {away_team.name}"
        
        # 1. Send to Home Team Fans
        data_home = {"type": "FULL_TIME", "match_id": str(match_id), "reason": f"Following {home_team.name}"}
        NotificationService.send_push_to_topic(f"team_{home_team.id}", title, body, data_home, 'FULL_TIME')
        
        # 2. Send to Away Team Fans
        data_away = {"type": "FULL_TIME", "match_id": str(match_id), "reason": f"Following {away_team.name}"}
        NotificationService.send_push_to_topic(f"team_{away_team.id}", title, body, data_away, 'FULL_TIME')
        
        # 3. Send to Match Followers
        data_match = {"type": "FULL_TIME", "match_id": str(match_id), "reason": "Saved Match"}
        NotificationService.send_push_to_topic(f"match_{match_id}", title, body, data_match, 'FULL_TIME')

        # 4. Send to League Followers
        data_league = {"type": "FULL_TIME", "match_id": str(match_id), "reason": "Following League"}
        NotificationService.send_push_to_topic(f"league_{league_id}", title, body, data_league, 'FULL_TIME')
    
    @staticmethod
    def send_lineup_alert(home_team, away_team, match_id, league_id=None):
        """
        Sends Lineup Confirmation to Team Topics, Match Topic, and League Topic.
        """
        title = "📋 Lineups Released"
        body = f"Starting XI is now available for {home_team.name} vs {away_team.name}"
        
        data_home = {"type": "LINEUPS", "match_id": str(match_id), "reason": f"Following {home_team.name}"}
        NotificationService.send_push_to_topic(f"team_{home_team.id}", title, body, data_home, 'LINEUPS')

        data_away = {"type": "LINEUPS", "match_id": str(match_id), "reason": f"Following {away_team.name}"}
        NotificationService.send_push_to_topic(f"team_{away_team.id}", title, body, data_away, 'LINEUPS')
        
        data_match = {"type": "LINEUPS", "match_id": str(match_id), "reason": "Saved Match"}
        NotificationService.send_push_to_topic(f"match_{match_id}", title, body, data_match, 'LINEUPS')

        if league_id:
            data_league = {"type": "LINEUPS", "match_id": str(match_id), "reason": "Following League"}
            NotificationService.send_push_to_topic(f"league_{league_id}", title, body, data_league, 'LINEUPS')
    
    @staticmethod
    def send_league_daily_update(league_name, match_count, league_id):
        """
        Sends a daily schedule summary for a league.
        """
        title = f"📅 {league_name} Schedule"
        body = f"There are {match_count} matches starting tomorrow in {league_name}. Don't miss out!"
        data = {"type": "SCHEDULE", "league_id": str(league_id), "reason": f"Following {league_name}"}
        
        NotificationService.send_push_to_topic(f"league_{league_id}", title, body, data, 'SCHEDULE')

    # --- Subscription Helpers ---
    @staticmethod
    def subscribe_tokens_to_topic(tokens, topic):
        NotificationService.ensure_firebase_initialized()
        if not tokens: return
        batch_size = 1000
        for i in range(0, len(tokens), batch_size):
            batch = tokens[i:i + batch_size]
            try:
                messaging.subscribe_to_topic(batch, topic)
            except Exception as e:
                print(f"Error subscribing to {topic}: {e}")

    @staticmethod
    def unsubscribe_tokens_from_topic(tokens, topic):
        NotificationService.ensure_firebase_initialized()
        if not tokens: return
        batch_size = 1000
        for i in range(0, len(tokens), batch_size):
            batch = tokens[i:i + batch_size]
            try:
                messaging.unsubscribe_from_topic(batch, topic)
            except Exception as e:
                print(f"Error unsubscribing from {topic}: {e}")