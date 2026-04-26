"""
Garmin data fetcher - run this script to generate data.json for the dashboard
Usage: python3 garmin_fetch.py
"""
import json, os, sys
from datetime import date, timedelta
from garminconnect import Garmin

def safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        print(f"  Warning: {fn.__name__} failed - {e}")
        return None

def run():
    token_dir = os.path.expanduser("~/.garminconnect")
    token_file = os.path.join(token_dir, "garmin_tokens.json")

    if os.path.exists(token_file):
        print("Found saved token, logging in without password...")
        client = Garmin()
        client.login(tokenstore=token_dir)
        print("Logged in via saved token\n")
    else:
        email = os.environ.get("GARMIN_EMAIL") or input("Garmin email: ")
        password = os.environ.get("GARMIN_PASSWORD") or input("Garmin password: ")
        client = Garmin(
            email=email,
            password=password,
            prompt_mfa=lambda: input("Enter the 6-digit code Garmin emailed you: ")
        )
        client.login(tokenstore=token_dir)
        print("Login successful — token saved. Future runs won't need your password.\n")

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    month_ago = (date.today() - timedelta(days=30)).isoformat()

    data = {}

    print("Fetching user profile...")
    profile = safe(client.get_user_profile) or {}
    summary = safe(client.get_user_summary, today) or {}
    data['profile'] = {
        'name': profile.get('displayName', 'Athlete'),
        'full_name': safe(client.get_full_name) or '',
    }

    print("Fetching activities (last 30)...")
    activities = safe(client.get_activities, 0, 30) or []
    act_list = []
    for a in activities[:20]:
        act_list.append({
            'name': a.get('activityName',''),
            'type': a.get('activityType',{}).get('typeKey',''),
            'date': a.get('startTimeLocal','')[:10],
            'distance_m': a.get('distance', 0),
            'duration_s': a.get('duration', 0),
            'avg_hr': a.get('averageHR', 0),
            'max_hr': a.get('maxHR', 0),
            'calories': a.get('calories', 0),
            'elevation_m': a.get('elevationGain', 0),
            'avg_speed': a.get('averageSpeed', 0),
            'aerobic_te': a.get('aerobicTrainingEffect', 0),
            'vo2max': a.get('vO2MaxValue', 0),
        })
    data['activities'] = act_list

    print("Fetching sleep data...")
    sleep = safe(client.get_sleep_data, yesterday) or {}
    sd = sleep.get('dailySleepDTO', {}) if sleep else {}
    data['sleep'] = {
        'score': sd.get('sleepScores', {}).get('overall', {}).get('value', 0) if sd else 0,
        'duration_s': sd.get('sleepTimeSeconds', 0) if sd else 0,
        'deep_s': sd.get('deepSleepSeconds', 0) if sd else 0,
        'rem_s': sd.get('remSleepSeconds', 0) if sd else 0,
        'light_s': sd.get('lightSleepSeconds', 0) if sd else 0,
        'awake_s': sd.get('awakeSleepSeconds', 0) if sd else 0,
        'avg_spo2': sd.get('averageSpO2Value', 0) if sd else 0,
        'avg_resp': sd.get('averageRespirationValue', 0) if sd else 0,
        'restless': sd.get('restlessMomentsCount', 0) if sd else 0,
        'avg_hrv': sleep.get('wellnessEpochRespirationDataDTOList', [{}])[0].get('hrvValue', 0) if sleep else 0,
    }

    print("Fetching HRV data...")
    hrv = safe(client.get_hrv_data, today) or {}
    hrv_sum = hrv.get('hrvSummary', {}) if hrv else {}
    data['hrv'] = {
        'weekly_avg': hrv_sum.get('weeklyAvg', 0),
        'last_night': hrv_sum.get('lastNight', 0),
        'status': hrv_sum.get('status', 'unknown'),
        'balanced_low': hrv_sum.get('balancedLow', 0),
        'balanced_high': hrv_sum.get('balancedHigh', 0),
    }

    print("Fetching body battery...")
    bb = safe(client.get_body_battery, today, today) or []
    if bb and isinstance(bb, list) and len(bb) > 0:
        bb_data = bb[0] if isinstance(bb[0], dict) else {}
        data['body_battery'] = {
            'charged': bb_data.get('charged', 0),
            'drained': bb_data.get('drained', 0),
            'end_val': bb_data.get('endTimestampGMT', 0),
        }
    else:
        data['body_battery'] = {'charged': 0, 'drained': 0, 'end_val': 0}

    print("Fetching heart rate...")
    hr = safe(client.get_heart_rates, today) or {}
    data['heart_rate'] = {
        'resting': hr.get('restingHeartRate', 0),
        'max': hr.get('maxHeartRate', 0),
        'min': hr.get('minHeartRate', 0),
        'last_7d_avg_resting': hr.get('lastSevenDaysAvgRestingHeartRate', 0),
    }

    print("Fetching stress...")
    stress = safe(client.get_stress_data, today) or {}
    data['stress'] = {
        'avg': stress.get('avgStressLevel', 0),
        'max': stress.get('maxStressLevel', 0),
        'rest_duration': stress.get('restStressDuration', 0),
        'low_duration': stress.get('lowStressDuration', 0),
        'med_duration': stress.get('mediumStressDuration', 0),
        'high_duration': stress.get('highStressDuration', 0),
    }

    print("Fetching SpO2...")
    spo2 = safe(client.get_spo2_data, today) or {}
    data['spo2'] = {
        'avg': spo2.get('averageSpO2', 0),
        'lowest': spo2.get('lowestSpO2', 0),
    }

    print("Fetching training readiness...")
    tr = safe(client.get_training_readiness, today) or {}
    if isinstance(tr, list): tr = tr[0] if tr else {}
    data['training_readiness'] = {
        'score': tr.get('score', 0),
        'level': tr.get('level', ''),
        'feedback': tr.get('shortFeedback', ''),
    }

    print("Fetching training status...")
    ts = safe(client.get_training_status, today) or {}
    if isinstance(ts, list): ts = ts[-1] if ts else {}
    if not isinstance(ts, dict): ts = {}

    vo2_generic = ts.get('mostRecentVO2Max', {}).get('generic', {}) if isinstance(ts.get('mostRecentVO2Max'), dict) else {}
    vo2_value = vo2_generic.get('vo2MaxPreciseValue', 0) if isinstance(vo2_generic, dict) else 0

    ts_per_device = ts.get('mostRecentTrainingStatus', {}).get('latestTrainingStatusData', {}) if isinstance(ts.get('mostRecentTrainingStatus'), dict) else {}
    device_status = next(iter(ts_per_device.values()), {}) if isinstance(ts_per_device, dict) else {}
    if not isinstance(device_status, dict): device_status = {}

    load_per_device = ts.get('mostRecentTrainingLoadBalance', {}).get('metricsTrainingLoadBalanceDTOMap', {}) if isinstance(ts.get('mostRecentTrainingLoadBalance'), dict) else {}
    device_load = next(iter(load_per_device.values()), {}) if isinstance(load_per_device, dict) else {}
    if not isinstance(device_load, dict): device_load = {}

    acute = device_status.get('acuteTrainingLoadDTO', {}) if isinstance(device_status.get('acuteTrainingLoadDTO'), dict) else {}

    data['training_status'] = {
        'status': device_status.get('trainingStatusFeedbackPhrase', ''),
        'load': acute.get('dailyTrainingLoadAcute', 0),
        'load_chronic': acute.get('dailyTrainingLoadChronic', 0),
        'acwr': acute.get('dailyAcuteChronicWorkloadRatio', 0),
        'acwr_status': acute.get('acwrStatus', ''),
        'fitness_trend': device_status.get('fitnessTrend', 0),
        'load_balance': device_load.get('trainingBalanceFeedbackPhrase', ''),
        'monthly_aerobic_low': device_load.get('monthlyLoadAerobicLow', 0),
        'monthly_aerobic_high': device_load.get('monthlyLoadAerobicHigh', 0),
        'monthly_anaerobic': device_load.get('monthlyLoadAnaerobic', 0),
        'vo2max': vo2_value,
    }

    print("Fetching max metrics (VO2 max)...")
    mm = safe(client.get_max_metrics, today) or {}
    if isinstance(mm, list): mm = mm[-1] if mm else {}
    if not isinstance(mm, dict): mm = {}
    data['vo2max'] = {
        'value': mm.get('generic', {}).get('vo2MaxPreciseValue', 0) or vo2_value,
    }

    print("Fetching respiration...")
    resp = safe(client.get_respiration_data, today) or {}
    data['respiration'] = {
        'avg': resp.get('avgWakingRespirationValue', 0),
        'highest': resp.get('highestRespirationValue', 0),
        'lowest': resp.get('lowestRespirationValue', 0),
    }

    print("Fetching race predictions...")
    rp = safe(client.get_race_predictions) or {}
    data['race_predictions'] = {
        'five_k': rp.get('time5K', 0),
        'ten_k': rp.get('time10K', 0),
        'half_marathon': rp.get('timeHalfMarathon', 0),
        'marathon': rp.get('timeMarathon', 0),
    }

    def _score_value(obj, key):
        if not isinstance(obj, dict): return 0
        v = obj.get(key, 0)
        if isinstance(v, dict): return v.get('value', 0)
        return v if isinstance(v, (int, float)) else 0

    def _score_level(obj, key):
        if not isinstance(obj, dict): return ''
        v = obj.get(key, '')
        if isinstance(v, dict): return v.get('level', '')
        return obj.get('classification', '') or obj.get(key + 'Classification', '') or ''

    print("Fetching endurance score...")
    es = safe(client.get_endurance_score, today) or {}
    if isinstance(es, list): es = es[-1] if es else {}
    data['endurance_score'] = {
        'overall': _score_value(es, 'overallScore'),
        'level': _score_level(es, 'overallScore'),
    }

    print("Fetching hill score...")
    hs = safe(client.get_hill_score, today) or {}
    if isinstance(hs, list): hs = hs[-1] if hs else {}
    data['hill_score'] = {
        'value': _score_value(hs, 'hillScore'),
        'level': _score_level(hs, 'hillScore'),
    }

    print("Fetching daily steps...")
    steps = safe(client.get_daily_steps, week_ago, today) or []
    total_steps = sum(d.get('totalSteps', 0) for d in steps if isinstance(d, dict))
    data['steps'] = {
        'weekly_total': total_steps,
        'daily_avg': total_steps // max(len(steps), 1),
    }

    print("Fetching intensity minutes...")
    im_list = safe(client.get_weekly_intensity_minutes, week_ago, today) or []
    im_latest = im_list[-1] if isinstance(im_list, list) and im_list else {}
    if not isinstance(im_latest, dict): im_latest = {}
    data['intensity'] = {
        'moderate': im_latest.get('moderateValue', 0) or im_latest.get('weeklyModerateMinutes', 0),
        'vigorous': im_latest.get('vigorousValue', 0) or im_latest.get('weeklyVigorousMinutes', 0),
        'goal': im_latest.get('weeklyGoal', 0) or im_latest.get('weeklyGoalMinutes', 0),
    }

    print("Fetching running tolerance...")
    rt_list = safe(client.get_running_tolerance, month_ago, today) or []
    rt_latest = rt_list[-1] if isinstance(rt_list, list) and rt_list else {}
    if not isinstance(rt_latest, dict): rt_latest = {}
    data['running_tolerance'] = {
        'value': rt_latest.get('runningTolerance', 0) or rt_latest.get('value', 0),
    }

    print("Fetching morning readiness...")
    mr = safe(client.get_morning_training_readiness, today) or {}
    if isinstance(mr, list): mr = mr[-1] if mr else {}
    if not isinstance(mr, dict): mr = {}
    data['morning_readiness'] = {
        'score': mr.get('score', 0),
        'level': mr.get('level', ''),
    }

    print("Fetching scheduled workouts (Runna sync)...")
    today_d = date.today()
    today_iso = today_d.isoformat()
    scheduled = []
    for delta in (0, 1, 2, 3):  # this month + next 3
        ym = today_d.replace(day=1)
        for _ in range(delta):
            ym = (ym.replace(day=28) + timedelta(days=4)).replace(day=1)
        sw = safe(client.get_scheduled_workouts, ym.year, ym.month) or {}
        for item in sw.get('calendarItems', []) if isinstance(sw, dict) else []:
            if not isinstance(item, dict):
                continue
            iso = item.get('date')
            title = item.get('title') or ''
            if not iso or not title:
                continue
            if iso < today_iso:  # only upcoming
                continue
            scheduled.append({
                'date': iso,
                'title': title,
                'sport': item.get('sportTypeKey'),
                'workout_id': item.get('workoutId'),
                'is_race': item.get('isRace'),
                'item_type': item.get('itemType'),
            })
    # Dedupe by (date, title) keeping first
    seen = set()
    deduped = []
    for w in scheduled:
        key = (w['date'], w['title'])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(w)
    deduped.sort(key=lambda x: (x['date'], x['title']))
    data['scheduled_workouts'] = deduped
    print(f"  Found {len(deduped)} upcoming scheduled workouts/races")

    data['fetched_at'] = today
    data['fetched_time'] = str(__import__('datetime').datetime.now().strftime('%H:%M'))

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'garmin_data.json')
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n✓ Data saved to {output_path}")
    print(f"  Activities: {len(act_list)}")
    print(f"  VO2 max: {data['vo2max']['value']}")
    print(f"  RHR: {data['heart_rate']['resting']}")
    print(f"  Sleep score: {data['sleep']['score']}")
    print(f"  Training readiness: {data['training_readiness']['score']}")

if __name__ == '__main__':
    run()
