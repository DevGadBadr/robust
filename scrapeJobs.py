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
        jobsDict: dict =jobsFile['jobs']
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


    def addGetUrlJob(self, **kwargs):
        url = kwargs.get("url")
        owner = kwargs.get("owner")
        job = (getUrlJob,{"url":url})
        self.actions.append(job)
        self.lastExecuted = False
        self.saveJobIfNotExist(("GetUrl",{"url":url}),owner)

    def addInputFieldJob(self, **kwargs):
        field_identifier = kwargs.get("field_identifier")
        identifier_value = kwargs.get("identifier_value")
        value = kwargs.get("value")
        job = (inputFieldJob,{"field_identifier":field_identifier,"identifier_value":identifier_value,"value":value})
        self.actions.append(job)
        self.lastExecuted = False

    def addClickButtonJob(self, **kwargs):
        button_identifier = kwargs.get("button_identifier")
        identifier_value = kwargs.get("identifier_value")
        job = (clickButtonJob,{"button_identifier":button_identifier,"identifier_value":identifier_value})
        self.actions.append(job)
        self.lastExecuted = False

    def getUrlAction(self):
        action, kwargs = self.actions[0]
        action(self.driver, **kwargs)
        return "Done"

    def executeNextAction(self):
        actionsLength = len(self.actions)
        if actionsLength == 1:
            if not self.lastExecuted:
                function, kwargs = self.actions[0]
                function(self.driver, **kwargs)
                self.lastExecuted = True
                self.firstExecuted = True
                print("Done")
                return
        if actionsLength > 1:
            if self.executePosition+1 == actionsLength:
                if not self.lastExecuted:
                    function, kwargs = self.actions[self.executePosition]
                    result = function(self.driver, **kwargs)
                    print(result)
                    self.lastExecuted = True
                return
            function, kwargs = self.actions[self.executePosition]
            result = function(self.driver, **kwargs)
            print(result)
            self.executePosition += 1
            self.firstExecuted = False

    def executePreviousAction(self):
        actionsLength = len(self.actions)
        if actionsLength == 1:
            self.driver.back()
            self.lastExecuted = False
            print("Done")
            return
        if actionsLength > 1:
            if self.executePosition == 0:
                if not self.firstExecuted:
                    function, kwargs = self.actions[self.executePosition]
                    result = function(self.driver, **kwargs)
                    print(result)
                    self.firstExecuted = True
                else:
                    self.driver.back()
                return
            function, kwargs = self.actions[self.executePosition-1]
            result = function(self.driver, **kwargs)
            print(result)
            self.executePosition -= 1
            self.lastExecuted = False

class zenHrAutomation(abstractScrapeJob):
    # Identifiers for this scrape job
    email_field = {"identifierType": "id", "identifierValue": "email"}
    email_submit_button = {"identifierType": "id", "identifierValue": "submit-email"}
    password_field = {"identifierType": "id", "identifierValue": "user_password"}
    login_submit_button = {"identifierType": "text", "identifierValue": "Login"}
   
    def __init__(self, driver, **kwargs):
        super().__init__(driver, **kwargs)