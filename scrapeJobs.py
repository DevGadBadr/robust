import json
from scrapeJobsHelpers import getUrlJob, inputFieldJob, clickButtonJob, extractTextJob, extractLinksJob


def normalizeContext(context):
    """Drop an empty frame/shadow context so untouched jobs keep their old shape."""
    if not isinstance(context, dict):
        return None
    frames = context.get("frames") or []
    hosts = context.get("hosts") or []
    if not frames and not hosts:
        return None
    cleaned = {}
    if frames:
        cleaned["frames"] = frames
    if hosts:
        cleaned["hosts"] = hosts
    return cleaned


def buildKwargs(fields, uuid, jobtype, position, context=None):
    kwargs = dict(fields)
    kwargs["uuid"] = uuid
    kwargs["jobtype"] = jobtype
    kwargs["position"] = position
    context = normalizeContext(context)
    if context is not None:
        kwargs["context"] = context
    return kwargs


# The fields that decide whether a re-saved job is the same job. "context" is
# part of it: the same selector in a different frame or shadow root is a
# different target.
COMPARE_FIELDS = {
    "GetUrl": ("url",),
    "InputField": ("field_identifier", "identifier_value", "value", "context"),
    "ClickButton": ("button_identifier", "identifier_value", "context"),
    "ExtractText": ("text_identifier", "identifier_value", "context"),
    "ExtractLinks": ("link_identifier", "identifier_value", "context"),
}


class abstractScrapeJob:
    def __init__(self, driver):
        self.driver = driver
        self.executePosition = 0
        self.firstExecuted = False
        self.lastExecuted = False

    def initiateActions(self, actions):
        self.actions = actions

    def _clampExecuteCursor(self):
        """Keep executePosition in [0, len(actions)] and sync lastExecuted."""
        n = len(getattr(self, "actions", []) or [])
        if self.executePosition < 0:
            self.executePosition = 0
        elif self.executePosition > n:
            self.executePosition = n
        self.lastExecuted = n == 0 or self.executePosition >= n

    def saveJobIfNotExist(self, job, owner):
        with open("./resources/jobs.json","r") as f:
            jobsFile = json.load(f)
        jobsDict:dict = jobsFile['jobs']
        updateFlag = False

        if owner in jobsDict.keys():
            jobs:list = jobsDict[owner]
            jobType = job[1]['jobtype']
            jobuuid = job[1]['uuid']
            fields = COMPARE_FIELDS.get(jobType, ())
            for existingJob in jobs:
                if existingJob[1].get('uuid') != jobuuid:
                    continue
                if all(existingJob[1].get(name) == job[1].get(name) for name in fields):
                    self.actions.pop()
                    self._clampExecuteCursor()
                    return "Job Exists"
                # Find Related Action
                existAction = None
                for action in self.actions:
                    if action[1]['uuid'] == jobuuid:
                        existAction = action
                        break
                for name in fields:
                    value = job[1].get(name)
                    if value is None:
                        existingJob[1].pop(name, None)
                        if existAction is not None:
                            existAction[1].pop(name, None)
                    else:
                        existingJob[1][name] = value
                        if existAction is not None:
                            existAction[1][name] = value
                updateFlag = True
                break

            if not updateFlag:
                jobs.append(job)
                jobsDict[owner] = jobs
        else:
            jobs = [job]
            jobsDict[owner] = jobs
        with open("./resources/jobs.json",'w') as f:
            json.dump(jobsFile, f)
        if updateFlag:
            self.actions.pop()
            self._clampExecuteCursor()
            return "Job Updated"
        return "Job Saved"

    def deleteJob(self, uuid, owner):
        for action in self.actions:
            if action[1].get("uuid") == uuid:
                actionIndex = self.actions.index(action)
                self.actions.remove(action)
                print(f"Deleted job from actions with uuid: {uuid} for owner: {owner}")
                if actionIndex < self.executePosition:
                    self.executePosition-=1
                break
        self._clampExecuteCursor()
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
                json.dump(jobsFile, f)

    def addJob(self, function, jobtype, fields, **kwargs):
        owner = kwargs.get("owner")
        uuid = kwargs.get("uuid")
        context = kwargs.get("context")
        position = len(self.actions)
        self.actions.append((function, buildKwargs(fields, uuid, jobtype, position, context)))
        self._clampExecuteCursor()
        # New action is runnable work; clear finished even if cursor was parked at end.
        if len(self.actions) > 0:
            self.lastExecuted = False
        return self.saveJobIfNotExist((jobtype, buildKwargs(fields, uuid, jobtype, position, context)), owner)

    def addGetUrlJob(self, **kwargs):
        return self.addJob(getUrlJob, "GetUrl", {"url": kwargs.get("url")}, **kwargs)

    def addInputFieldJob(self, **kwargs):
        return self.addJob(inputFieldJob, "InputField", {
            "field_identifier": kwargs.get("field_identifier"),
            "identifier_value": kwargs.get("identifier_value"),
            "value": kwargs.get("value"),
        }, **kwargs)

    def addClickButtonJob(self, **kwargs):
        return self.addJob(clickButtonJob, "ClickButton", {
            "button_identifier": kwargs.get("button_identifier"),
            "identifier_value": kwargs.get("identifier_value"),
        }, **kwargs)

    def addExtractTextJob(self, **kwargs):
        return self.addJob(extractTextJob, "ExtractText", {
            "text_identifier": kwargs.get("text_identifier"),
            "identifier_value": kwargs.get("identifier_value"),
        }, **kwargs)

    def addExtractLinksJob(self, **kwargs):
        return self.addJob(extractLinksJob, "ExtractLinks", {
            "link_identifier": kwargs.get("link_identifier"),
            "identifier_value": kwargs.get("identifier_value"),
        }, **kwargs)

    def executeNextAction(self):
        self._clampExecuteCursor()
        n = len(self.actions)
        if self.executePosition >= n:
            self.lastExecuted = True
            return "End of actions", "end", "forward", None
        function, kwargs = self.actions[self.executePosition]
        kwargs["direction"] = "forward"
        result = function(self.driver, **kwargs)
        self.executePosition += 1
        self.firstExecuted = False
        self.lastExecuted = self.executePosition >= n
        return result

    def executePreviousAction(self):
        self._clampExecuteCursor()
        n = len(self.actions)
        if n == 0:
            return "Previous Done", "back", "backward", None
        # Single-step jobs unwind via browser history, matching prior behavior.
        if n == 1:
            self.driver.back()
            self.executePosition = 0
            self.lastExecuted = False
            return "Previous Done", "back", "backward", None
        if self.executePosition == 0:
            if not self.firstExecuted:
                function, kwargs = self.actions[0]
                kwargs["direction"] = "backward"
                result = function(self.driver, **kwargs)
                self.firstExecuted = True
                return result
            self.driver.back()
            return "Previous Done", "back", "backward", None
        function, kwargs = self.actions[self.executePosition - 1]
        kwargs["direction"] = "backward"
        result = function(self.driver, **kwargs)
        self.executePosition -= 1
        self.lastExecuted = False
        return result