import json
from scrapeJobsHelpers import getUrlJob, inputFieldJob, clickButtonJob

class abstractScrapeJob:
    def __init__(self, driver):
        self.driver = driver
        self.executePosition = 0
        self.firstExecuted = False
        self.lastExecuted = False

    def initiateActions(self, actions):
        self.actions = actions

    def saveJobIfNotExist(self, job, owner):
        with open("./resources/jobs.json","r") as f:
            jobsFile = json.load(f)
        jobsDict:dict = jobsFile['jobs']
        
        if owner in jobsDict.keys():
            jobs:list = jobsDict[owner]
            jobType = job[1]['jobtype']  
            jobuuid = job[1]['uuid']
            updateFlag = False
            existAction = None
            for existingJob in jobs:
                if existingJob[1]['uuid'] == jobuuid:
                    if jobType == "GetUrl":
                        if existingJob[1]['url'] == job[1]['url']:
                            self.actions.pop()
                            return "Job Exists"
                        else:
                            # Find Related Action
                            for action in self.actions:
                                if action[1]['uuid'] == jobuuid:
                                    existAction = action
                                    break
                            existingJob[1]['url'] = job[1]['url']
                            existAction[1]['url'] = job[1]['url']
                            updateFlag = True
                    if jobType == "ClickButton":
                        if existingJob[1]['button_identifier'] == job[1]['button_identifier'] and existingJob[1]['identifier_value'] == job[1]['identifier_value']:
                            self.actions.pop()
                            return "Job Exists"
                        else:
                            # Find Related Action
                            for action in self.actions:
                                if action[1]['uuid'] == jobuuid:
                                    existAction = action
                                    break
                            existingJob[1]['button_identifier'] = job[1]['button_identifier']
                            existingJob[1]['identifier_value'] = job[1]['identifier_value']
                            existAction[1]['button_identifier'] = job[1]['button_identifier']
                            existAction[1]['identifier_value'] = job[1]['identifier_value']
                            updateFlag = True
                    if jobType == "InputField":
                        if existingJob[1]['field_identifier'] == job[1]['field_identifier'] and existingJob[1]['identifier_value'] == job[1]['identifier_value'] and existingJob[1]['value'] == job[1]['value']:
                            self.actions.pop()
                            return "Job Exists"
                        else:
                            # Find Related Action
                            for action in self.actions:
                                if action[1]['uuid'] == jobuuid:
                                    existAction = action
                                    break
                            existingJob[1]['field_identifier'] = job[1]['field_identifier']
                            existingJob[1]['identifier_value'] = job[1]['identifier_value']
                            existingJob[1]['value'] = job[1]['value']
                            existAction[1]['field_identifier'] = job[1]['field_identifier']
                            existAction[1]['identifier_value'] = job[1]['identifier_value']
                            existAction[1]['value'] = job[1]['value']
                            updateFlag = True
                    break
                    
            if not updateFlag:
                jobs.append(job)
                jobsDict[owner] = jobs
        else:
            jobs = [job]
            jobsDict[owner] = jobs
        with open("./resources/jobs.json",'w') as f:
            json.dump({"jobs": jobsDict} , f)
        if updateFlag:
            self.actions.pop()
            return "Job Updated"
        return "Job Saved"

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
        jobtype = "GetUrl"
        job = (getUrlJob, {"url":url, "uuid": uuid, "jobtype": jobtype, "position":(len(self.actions))})
        self.actions.append(job)
        self.lastExecuted = False
        saveResult = self.saveJobIfNotExist(("GetUrl",{"url":url, "uuid": uuid, "jobtype": jobtype, "position":(len(self.actions)-1)}), owner)
        return saveResult

    def addInputFieldJob(self, **kwargs):
        field_identifier = kwargs.get("field_identifier")
        identifier_value = kwargs.get("identifier_value")
        value = kwargs.get("value")
        uuid = kwargs.get("uuid")
        joptype = "InputField"
        owner = kwargs.get("owner")
        job = (inputFieldJob, {"field_identifier":field_identifier,"identifier_value":identifier_value,"value":value, "uuid": uuid, "jobtype": joptype, "position":(len(self.actions))})
        self.actions.append(job)
        self.lastExecuted = False
        saveResult = self.saveJobIfNotExist(("InputField", {"field_identifier":field_identifier,"identifier_value":identifier_value,"value":value, "uuid": uuid, "jobtype": joptype, "position":(len(self.actions)-1)}), owner)
        return saveResult

    def addClickButtonJob(self, **kwargs):
        button_identifier = kwargs.get("button_identifier")
        identifier_value = kwargs.get("identifier_value")
        uuid = kwargs.get("uuid")
        joptype = "ClickButton"
        owner = kwargs.get("owner")
        job = (clickButtonJob, {"button_identifier":button_identifier,"identifier_value":identifier_value, "uuid": uuid, "jobtype": joptype, "position":(len(self.actions))})
        self.actions.append(job)
        self.lastExecuted = False
        saveResult = self.saveJobIfNotExist(("ClickButton", {"button_identifier":button_identifier,"identifier_value":identifier_value, "uuid": uuid, "jobtype": joptype, "position":(len(self.actions)-1)}), owner)
        return saveResult

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
            if self.executePosition+1 == actionsLength or self.executePosition == actionsLength:
                if not self.lastExecuted:
                    function, kwargs = self.actions[self.executePosition]
                    kwargs['direction'] = "forward"
                    result = function(self.driver, **kwargs)
                    self.lastExecuted = True
                    self.executePosition = len(self.actions)
                    print(self.executePosition, actionsLength, self.lastExecuted, "last")
                    return result
                self.executePosition = len(self.actions)
                return "End of actions", "end", "forward"
            function, kwargs = self.actions[self.executePosition]
            kwargs['direction'] = "forward"
            result = function(self.driver, **kwargs)
            self.executePosition += 1
            self.firstExecuted = False
            print(self.executePosition, actionsLength, self.lastExecuted, "next")
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