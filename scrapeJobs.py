APP_URLS = {
    "Google":"https://www.google.com",
    "Facebook":"https://www.facebook.com",
    "YouTube":"https://www.youtube.com",
    "TikTok":"https://www.tiktok.com",
    "Instagram":"https://www.instagram.com",
    "X":"https://www.x.com",
    "ZenHR":"https://app.zenhr.com/en/users/pre_login"
}

import json
from scrapeJobsHelpers import getUrlJob,inputFieldJob, clickButtonJob

class abstractScrapeJob:
    def __init__(self, driver):
        self.driver = driver
        self.executePosition = 0
        self.firstExecuted = False
        self.lastExecuted = False

    def initiateActions(self,actions):
        self.actions = actions

    def saveJobIfNotExist(self, job, owner):
        with open("./resources/jobs.json","r") as f:
            jobsFile = json.load(f)
        jobsDict:dict = jobsFile['jobs']
        if owner in jobsDict.keys():
            jobs:list = jobsDict[owner]
            for existingJob in jobs:
                if existingJob[1]['url'] == job[1]['url']:
                    print("Job already exists. Not saving.")
                    return
            jobs.append(job)
            jobsDict[owner] = jobs
        else:
            jobs = [job]
            jobsDict[owner] = jobs
        with open("./resources/jobs.json",'w') as f:
            json.dump({"jobs": jobsDict} , f)
        print(f"Added Get URL job with url: {job[1]['url']} for owner: {owner}")

    def deleteJob(self, uuid, owner):
        for action in self.actions:
            if action[1].get("uuid") == uuid:
                self.actions.remove(action)
                print(f"Deleted job from actions with uuid: {uuid} for owner: {owner}")
                break
        with open("./resources/jobs.json","r") as f:
            jobsFile = json.load(f)
        jobsDict:dict =jobsFile['jobs']
        if owner in jobsDict.keys():
            jobs:list = jobsDict[owner]
            for existingJob in jobs:
                if existingJob[1].get("uuid") == uuid:
                    jobs.remove(existingJob)
                    print(f"Deleted job with uuid: {uuid} for owner: {owner}")
                    break
            jobsDict[owner] = jobs
            with open("./resources/jobs.json","w") as f:
                json.dump({"jobs": jobsDict} , f)

    def addGetUrlJob(self, **kwargs):
        url = kwargs.get("url")
        owner = kwargs.get("owner")
        uuid = kwargs.get("uuid")
        joptype = "GetUrl"
        job = (getUrlJob,{"url":url, "uuid": uuid, "jobtype": joptype})
        self.actions.append(job)
        self.lastExecuted = False
        self.saveJobIfNotExist(("GetUrl",{"url":url, "uuid": uuid, "jobtype": joptype}), owner)

    def addInputFieldJob(self, **kwargs):
        field_identifier = kwargs.get("field_identifier")
        identifier_value = kwargs.get("identifier_value")
        value = kwargs.get("value")
        uuid = kwargs.get("uuid")
        joptype = "InputField"
        job = (inputFieldJob,{"field_identifier":field_identifier,"identifier_value":identifier_value,"value":value, "uuid": uuid, "jobtype": joptype})
        self.actions.append(job)
        self.lastExecuted = False

    def addClickButtonJob(self, **kwargs):
        button_identifier = kwargs.get("button_identifier")
        identifier_value = kwargs.get("identifier_value")
        uuid = kwargs.get("uuid")
        joptype = "ClickButton"
        job = (clickButtonJob,{"button_identifier":button_identifier,"identifier_value":identifier_value, "uuid": uuid, "jobtype": joptype})
        self.actions.append(job)
        self.lastExecuted = False

    def executeNextAction(self):
        actionsLength = len(self.actions)
        if actionsLength == 1:
            if not self.lastExecuted:
                function, kwargs = self.actions[0]
                kwargs['direction'] = "forward"
                result = function(self.driver, **kwargs)
                self.lastExecuted = True
                self.firstExecuted = True
                return result
        if actionsLength > 1:
            if self.executePosition+1 == actionsLength:
                if not self.lastExecuted:
                    function, kwargs = self.actions[self.executePosition]
                    kwargs['direction'] = "forward"
                    result = function(self.driver, **kwargs)
                    self.lastExecuted = True
                    return result
            function, kwargs = self.actions[self.executePosition]
            kwargs['direction'] = "forward"
            result = function(self.driver, **kwargs)
            self.executePosition += 1
            self.firstExecuted = False
            return result

    def executePreviousAction(self):
        actionsLength = len(self.actions)
        if actionsLength == 1:
            self.driver.back()
            self.lastExecuted = False
            return "Previous Done", "back", "backward"
        if actionsLength > 1:
            if self.executePosition == 0:
                if not self.firstExecuted:
                    function, kwargs = self.actions[self.executePosition]
                    kwargs['direction'] = "backward"
                    result = function(self.driver, **kwargs)
                    self.firstExecuted = True
                    return result
                else:
                    self.driver.back()
                    return "Previous Done", "back", "backward"
            function, kwargs = self.actions[self.executePosition-1]
            kwargs['direction'] = "backward"
            result = function(self.driver, **kwargs)
            self.executePosition -= 1
            self.lastExecuted = False
            return result

class zenHrAutomation(abstractScrapeJob):
    # Identifiers for this scrape job
    email_field = {"identifierType": "id", "identifierValue": "email"}
    email_submit_button = {"identifierType": "id", "identifierValue": "submit-email"}
    password_field = {"identifierType": "id", "identifierValue": "user_password"}
    login_submit_button = {"identifierType": "text", "identifierValue": "Login"}
   
    def __init__(self, driver, **kwargs):
        super().__init__(driver, **kwargs)