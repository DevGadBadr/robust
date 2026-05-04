APP_URLS = {
    "Google":"https://www.google.com",
    "Facebook":"https://www.facebook.com",
    "YouTube":"https://www.youtube.com",
    "TikTok":"https://www.tiktok.com",
    "Instagram":"https://www.instagram.com",
    "X":"https://www.x.com",
    "ZenHR":"https://app.zenhr.com/en/users/pre_login"
}

class abstractScrapeJob:
    def __init__(self, driver):
        self.driver = driver
        self.executePostion = 0

    def initiateActions(self,actions):
        self.actions = actions

    def getUrlAction(self):
        action, kwargs = self.actions[0]
        action(self.driver, **kwargs)
        return "Done"

    def executeNextAction(self):
        if self.executePostion < len(self.actions):
            action, kwargs = self.actions[self.executePostion]
            result = action(self.driver, **kwargs)
            self.executePostion += 1
            return(result)
        else:
           return "No more actions to execute"

    def executePreviousAction(self):
        if self.executePostion > 0:
            self.executePostion -= 1
            action, kwargs = self.actions[self.executePostion]
            action(self.driver, **kwargs)
        else:
            return "No previous actions to execute"

class zenHrAutomation(abstractScrapeJob):
    # Identifiers for this scrape job
    email_field = {"identifierType": "id", "identifierValue": "email"}
    email_submit_button = {"identifierType": "id", "identifierValue": "submit-email"}
    password_field = {"identifierType": "id", "identifierValue": "user_password"}
    login_submit_button = {"identifierType": "text", "identifierValue": "Login"}
   
    def __init__(self, driver, **kwargs):
        super().__init__(driver, **kwargs)