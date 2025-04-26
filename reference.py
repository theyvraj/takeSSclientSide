# following these view functions
for https://rankfiller.com/seotools/api/timetrackerscreen/
@csrf_exempt 
def doctortimescreens(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode('utf-8'))
            get_user = data.get('user', '')
            get_datetime = data.get('datetime', '')
            get_screenshots = data.get('screenshots', '')
            activity_log = data.get('activity_log', '')

            date_folder = datetime.now().strftime('%Y-%m-%d')
            screens_dir = os.path.join(settings.MEDIA_ROOT, 'screens')
            os.makedirs(screens_dir, exist_ok=True)

            user_folder = os.path.join(screens_dir, get_user)
            os.makedirs(user_folder, exist_ok=True)

            # Create directory paths
            date_user_dir = os.path.join(user_folder, date_folder)
            os.makedirs(date_user_dir, exist_ok=True)  # Create folders if they don't exist

            try:
                TD_userquery=timetrack_User.objects.get(user_name=get_user)                
            except timetrack_User.DoesNotExist:
                TD_userquery=timetrack_User(user_name=get_user, created_at=datetime.now())
                TD_userquery.save()

            if TD_userquery.trackstatus:
                
                for each in activity_log:
                    if not timetracking_log.objects.filter(user_id=TD_userquery, activity_start=each["start_time"]).exists():
                        timequery=timetracking_log(user_id=TD_userquery, activity_start=each["start_time"], activity_end=each["end_time"])
                        timequery.save()
                
                for each in get_screenshots:
                    
                    getkey=list(each.keys())[0]
                    screenshot_filename = f"screenshot_{getkey}.png"
                    screenshot_filepath = os.path.join(date_user_dir, screenshot_filename)
                    # Save the screenshot as a file on the server
                    with open(screenshot_filepath, 'wb') as screenshot_file:
                        screenshot_file.write(base64.b64decode(each[getkey]))
                    
                    ssquery=timetracker(user_id=TD_userquery, activity_date=getkey, screenshot_data=screenshot_filename)
                    ssquery.save()

            getsettings=timetracker_setting.objects.all().first()
            
            data={
                "status":TD_userquery.trackstatus,
                "screen_shot_time":getsettings.screenshot_time,
                "log_time":getsettings.log_time,
                "update_time":getsettings.update_time,
            }

            return JsonResponse(data, safe=False)
        
        except Exception as e:
            #print("66666666666666666666666gggggggggggggggggggggfdfsdfsdfsdfsdfdfsdfsdfsdfsdfsdfsdfsdafsfsdfsdfsdfsdfsdfsd",e)
            return JsonResponse(False, safe=False)








#Time Tracker Application

@csrf_exempt 
def doctortimeerrorlog(request):
    if request.method == "POST":
        data = json.loads(request.body.decode('utf-8'))
        get_user = data.get('user', '')
        errorlog = data.get('errorlog', '')
        try:
            queryusertt=timetrack_User.objects.get(user_name=get_user)
        except timetrack_User.DoesNotExist:
            queryusertt=timetrack_User(user_name=get_user, created_at=datetime.now())
            queryusertt.save()

        if not 'Permission denied' in errorlog:
            savelog=timetrack_error(user_id=queryusertt,error_log=errorlog, created_at=datetime.now())
            savelog.save()
        
        #return JsonResponse(queryusertt.status, safe=False)
        return JsonResponse(False, safe=False)






for https://rankfiller.com/seotools/api/autoupdate/

@csrf_exempt
def check_autoupdate(request):
    if request.method =="POST":
        app_name=request.POST.get('appname')
        print(app_name)
        get_appquery = AutoUpdateExe.objects.filter(select_app=app_name).order_by('-app_version').first()
        print(get_appquery)
        exe_file_url = request.build_absolute_uri(get_appquery.exe_file.url) if get_appquery.exe_file else None

        message={"data":{"url":exe_file_url, "version":get_appquery.app_version}}
        return JsonResponse(message)
    else:
        return JsonResponse("Failed")


#Auto Update Functionality
class AutoUpdateExe(models.Model):
    TYPE_CHOICES = [
        ('geetatool', 'Geeta Tool'),
        ('timebooster', 'Time Booster'),
        ('trafficbot_node', 'Traffic Bot Node'),
        ('performaceSEO', 'PerformaceSEO(Traffic)'),
    ]
    select_app=models.CharField(max_length=255, null=True,choices=TYPE_CHOICES, verbose_name="Select App")
    app_version = models.FloatField(null=True)
    exe_file= models.FileField(upload_to=upload_to,blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if self.select_app and self.app_version:
            directory = os.path.join('files/autoupdate', self.select_app, str(self.app_version))
            full_path = os.path.join(settings.MEDIA_ROOT, directory)
            
            if os.path.exists(full_path):
                shutil.rmtree(full_path)
            os.makedirs(full_path, exist_ok=True)

        super().save(*args, **kwargs)


    def __str__(self):
        return self.select_app
    
    class timetracking_log(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(timetrack_User, on_delete=models.CASCADE, null=True, related_name="TrackLogUserId")
    activity_start= models.DateTimeField(blank=True, null=True)
    activity_end= models.DateTimeField(blank=True, null=True)

    class timetracker_setting(models.Model):
    screenshot_time=models.IntegerField(default=300, null=True, help_text="In Seconds")
    log_time=models.IntegerField(default=120, null=True, help_text="In Seconds")
    update_time=models.IntegerField(default=300, null=True, help_text="In Seconds")
#Time Tracker Application
    class timetracker_setting(models.Model):
    screenshot_time=models.IntegerField(default=300, null=True, help_text="In Seconds")
    log_time=models.IntegerField(default=120, null=True, help_text="In Seconds")
    update_time=models.IntegerField(default=300, null=True, help_text="In Seconds")

class timetrack_User(models.Model):
    id = models.AutoField(primary_key=True)
    user_name = models.CharField(max_length=500, null=True)
    shortname = models.CharField(max_length=500, null=True)
    department = models.ForeignKey(All_department, on_delete=models.CASCADE, blank=True, null=True)
    location = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    status= models.BooleanField(default=True)
    trackstatus = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.user_name}: {self.shortname}'



class timetrack_error(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(timetrack_User, on_delete=models.CASCADE, null=True, related_name="TrackErrorUserId")
    error_log= models.TextField(max_length=5000, null=True)
    created_at= models.DateTimeField(blank=True, null=True)