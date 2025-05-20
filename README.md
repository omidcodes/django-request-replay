Project Challenge: 
In a recent project, our team encountered a significant challenge with a stateful system that would revert to factory settings after reboots or power losses. Additionally, there was a need for a mechanism to accurately reproduce system states for debugging purposes when customers encountered internal server errors. Traditional methods like system logs and error-tracking tools such as Sentry were insufficient for replicating exact requests in a raw debugging environment.

My Approach to Fix it:
To tackle this issue, I developed a middleware solution within our Django Backend Core. This middleware was designed to record and save essential API requests to the database. This approach enabled us to restore the system to its last known state by replaying these saved requests. The middleware was engineered to capture request details upon their arrival, selectively save them based on predefined criteria, and utilize this data for effective system restoration.
This solution not only resolved the immediate issue of system state preservation but also enhanced our debugging capabilities, allowing for a more reliable and maintainable system.

Code Workflow Summary:
Capture API Request Details: When an API request is received by the Django web service, the middleware immediately captures its details.
Evaluate Saving Criteria: The middleware then evaluates whether the request meets the criteria to be saved (based on its method and the response status).
Database Saving: If the request is savable, the middleware creates an instance of `RequestInfoModel` and commits the request details to the database.
