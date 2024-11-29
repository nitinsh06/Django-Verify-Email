

<h1 style='text-align:center'>Email-Verification for Django</h1>

Email verification for new signups or new users is a two-step verification process and adds a layer for security for valid users.

<b> verify_email </b> is a django app that provides this functionality right of the bat without any complex implementation.

<hr>

## Version Update (2.0.0):

<hr>

> This version contains breaking changes and is not compatible with the previous version 1.0.9

### What's in this update
**Features:**
* Added feature for **re-requesting email** in case the previous email was lost or deleted by mistake
* Added a variable `REQUEST_NEW_EMAIL_TEMPLATE` where user can specify his custom template for requesting email again. More on this <a href='#resending-email-using-form'>here</a>.
* Added a Django form for requesting email with a field `email`.
* Support for DRF

Read about this feature <a href='#resending-email-using-form'>here</a>

**Bug Fixes:**
* Fixed a bug where the user was not able to request a new email using the previous link in case if the link expires.
 
 **Others**
 * Using exceptions instead of normal string errors
 * code cleanup

<hr><hr>

## The app takes care of :
* Settings user's is_active status to False.
* Generate hashed token for each user.
* Generate a verification link and send it to the user's email.
* Recieve a request from the verification link and verify for its validity.
* Activating the user's account.

## What you have to implement is :
* Three steps in <a href='#quickstart'>Quick start</a> below...

<b>Note : </b>The app is designed to be used right of the bat, however, further customizations options are also provided in <a href="#advance">Advance</a> section below.


## Installation

NOTE: Don't forget to activate the virtual environment if you have one.

```
pip install Django-Verify-Email
```

<p id='quickstart'>
<h2>Quick start</h2> <hr>
</p>

The steps to getting started are very simple. Like any other app, this can be installed easily by adding "verify_email" in your installed apps like:

<b>Note: </b>This documentation assumes that you already have a mail server configured for your project to send mails. 

if not, then your first step should be Step 0:

### Step 0 :-

--- Bypass this step if you already have these things set up for your project. ---

In your settings.py :
```
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_ID') 
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PW')

DEFAULT_FROM_EMAIL = 'noreply<no_reply@domain.com>'
```

## Main steps... <hr>

### Step 1 :-
Add "verify_email" to your INSTALLED_APPS setting like this:
```
    INSTALLED_APPS = [
        ...
        "verify_email.apps.VerifyEmailConfig",
    ]
```
<p id="step2">
<h3>Step 2 :-</h3>

Include the "verify_email" URLconf in your project urls.py like this:


```

urlpatterns = [
	...
	path('verification/', include('verify_email.urls')),	

]
```
</p>

<p id="step3">
<h3>Step 3 :-</h3>

Apply migrations...


```
python manage.py migrate
```
</p>



### Step 4 :-
For sending email from a signup form, in your views.py import:

```
...
from verify_email.email_handler import send_verification_email
```
Now in the function where you are validating the form:

```
...

def register_user(request):
    ...
    
    if form.is_valid():

        inactive_user = send_verification_email(request, form)
```

<b>Attention : </b>"send_verification_email()" takes two arguments, requests and form in order to set user's active status. 

The "inactive_user" that is returned by "send_verification_email()" contains a saved user object just like form.save() would do(with is_active status set as False), which you can further use to extract user information from cleaned_data dictionary, as shown below :

```
inactive_user.cleaned_data['email']

# Output: test-user123@gmail.com
```
The user is already being saved as inactive and you don't have to .save() it explicitly.

<b>If anything goes wrong in sending the verification link email, the user will not be saved, so that the user can try again.</b>



### At this point, you are good to go...
 Start the development server and signup with an email and you should be getting an email on the entered email with the default template for account activation. (You can provide your own HTML template. see <a href='#advance'>Advance Section</a>)

 <b>Note : </b>The app comes with default email templates which can be overriden. See <a href='#customemailtemplate'> Custom Email Templates</a>

# Verifying User's email : 

<h3 style='text-align:center'>Nothing...</h3><br>

That's right! , you don't have to implement any other code for validating users with their respective unique tokens and emails. 

<b>The app takes care of everything in the background.</b>

* When the user clicks on the verification link, it comes to :
    ```
    path('verification/', include('verify_email')),
    ```
    which you defined in your project's urls.py in <a href='#step2'>step 2</a> above.
* This pattern is further extended in this app's urls.py where it accepts encoded email and encoded hashed tokens from the verification link.
* It then checks for users by that email.
* If the user exists, it then checks for a token if it is valid for that user or not.
* If the token is valid, it activates the user's account by setting is_active attribute to True and last_login to timezone.now().
* If the token is already been redeemed or modified, you'll be redirected to a "verification failed" page.

#### This whole process from generating HMAC hashed token for each user to verify it for a unique user, is abstracted within the app 😃.



<p id="advance">

<h1>Advance</h1>

<p id="link-expiring">
<h2>Expiration of link and Resending emails :</h2>
If you want your link to expire after a certain amount of time, you can use signed links, <b>All you have to do is just set a variable in the settings.py file and BAMM! you got yourself a link that will expire after the specified time.</b><br>
It's that simple, just setting a variable. <br><br>
If you don't set this variable, the link will expire after being used at least once. 
<br>

The link, by default, does not expire until it has been used at least once, however, you can 
**change** this behavior by specifying the time as
"EXPIRE_AFTER" in settings.py. The variable can be set as :
* By default the time is considered in seconds, so if you set "EXPIRE_AFTER" as an integer, that will be considered in seconds.
* You can specify time unit for large times, max unit is days.
* **Its very simple** just suffix the "EXPIRE_AFTER" variable's value with a time unit from ["s", "m", "h", "d"]. (Keep in mind, the "m" here is minutes, not month)

**Example**

* If I have to make a link expire after **one-day**, then I'd do:
    * EXPIRE_AFTER = "1d"  # Will expire after one day from link generation

* If I have to make a link expire after **one-hour**, then I'd do:
    * EXPIRE_AFTER = "1h"  # Will expire after one hour from link generation
    
* If I have to make a link expire after **one-minute**, then I'd do:
    * EXPIRE_AFTER = "1m"  # Will expire after 1 minute from link generation

**Note:** By default, if you do not specify a unit, it'll be considered in seconds.
</p>

<p id="resending-email">
<h2>Re-Sending Email</h2> <hr>
</p>

A user can request a new verification link **For a specific no. of times** in case the previous one has expired. By default, a user can request
new link **two times** which, obviously can be modified by you.

Set a "MAX_RETRIES" variable in settings.py specifying the no. of times a user is allowed to request a new link.

After that no. is exceeded, the user will be automatically redirected to an error page showing that you have maxed out.

<p id="resending-email-using-link">
<h2>Re-Sending Email using previous link</h2> 
</p>
When the link expires, the user will be redirected to a page displaying that the link is expired and has a button to request a new email, now as long as the user hasn't exceeded max retries, the user can request a new email simply by clicking on that button.

<p id='resending-email-using-form'>
<h2>Resend Email using Email Form</h2> 
</p>

In case when previous email/link is lost or deleted by the client, they can request a new email by specifying their email.

The path for that is `https://yourdomain/verification/user/verify-email/request-new-link/`, at this path, there will be a form that will ask for the email of the registered user.

The pathname is `request-new-link-from-email` which you can use to create a button on your front end and redirect traffic to the request email page.
Something like:

```html
<a href="{% url 'request-new-link-from-email' %}">
```

This will redirect you to full path `/verification/user/verify-email/request-new-link/`

There are several checks done before sending an email again:
* if the email is registered and the user's account is not been activated
* the user hasn't exceeded max retry limit(set by you),

Then a new email will be sent to the given email.

The form template is supposed to be changed unless you are okay with the default template provided with the package.

To set your own custom template for form, set a variable name `REQUEST_NEW_EMAIL_TEMPLATE` in settings.py with the path of template you want to use. Example:
```py
REQUEST_NEW_EMAIL_TEMPLATE = 'mytemplates/mycustomtemplate.html'
```
and then your template will be displayed at the path.

**Making Form:** while making your custom template, keep in mind that the view will pass a variable named `form` to the provided template, this form will contain only 1 field `email`. Sample code that you can use while making your template is here:

```html
<form method='POST' >
            {% csrf_token %}
    
            <fieldset>
                {{form}}
            </fieldset>
    
            <div style="margin-top: 50px;">
                <button class="btn btn-outline-info" type="submit">Request New Email</button>
            </div>
</form>
```
You can apply your styles or whatever you want. (this code is used in the default template)


**NOTE:** This info is stored in the database so you have to apply migrations (<a href='#step3'>step 3</a>) to use this feature. 
</p>

<p id="customemailtemplate">

<h2>Custom Email Templates : </h2>

The app is packed with default HTML templates to handle the web pages but if you want to provide your own template you can do it by setting an attribute in settings.py :

```
HTML_MESSAGE_TEMPLATE = "path/to/html_template.html"

VERIFICATION_SUCCESS_TEMPLATE = "path/to/success.html"

VERIFICATION_FAILED_TEMPLATE = "path/to/failed.html"

REQUEST_NEW_EMAIL_TEMPLATE = "path/to/email.html"

LINK_EXPIRED_TEMPLATE = 'path/to/expired.html'

NEW_EMAIL_SENT_TEMPLATE  = 'path/to/new_email_sent.html'
```
```
SUBJECT = 'subject of email'

# default subject is: Email Verification Mail
```
</p>

## Inside Templates : <hr>

### Custom HTML Message Template :

Two variables are passed in context dict of "HTML_MESSAGE_TEMPLATE" :

* ```{{request}}``` : Which is the same request passed in to send_verification_email.
* ```{{link}}``` : Which contains verification link

<b>IMPORTANT : </b> if you are using custom html message template for email that has to be sent to user, <u>provide a <b>{{link}}</b> as a template tag to contain verification link.</u> 

<b>You Must Pass This In Your Template</b>. Otherwise, the sent mail will not contain the verification link.


For Ex :

```my_custom_email_message.html : ```

```
<div class="format-font" >
    <a href="{{link}}" class="my-button" >Verify</a>  # ----> The "link" variable is passed by the app's backend containing verification link.
</div>
```

----> "link" is a variable, that contains a verification link, and is passed in an HTML message template during sending the email to the user.


### Custom HTML Verification Success and Failed pages : 
<hr>

<b>Success :</b> 

Two variables are passed in the context dictionary of "VERIFICATION_SUCCESS_TEMPLATE" :

* ```{{mgs}}```: Which contains the message to be displayed on successful verification.
* ```{{link}}```: Which contains a redirect link to the login page.

<b>In template :</b>

```
<h1 style="text-align: center; color: white;">
    {{msg}}     # __--> message variable
</h1>

<a href="{{link}}" class="btn btn-primary">     # __--> Link of login page
    Login
</a>

```

<b>Failed :</b>

Only "{{msg}}" is passed for failed msg in the template.


<b>In template :</b>

```
<h1 style="text-align: center; color: white;">
    {{msg}}
</h1>
```



## Successful Verification :
After verification is successful, you might want to redirect the user to the login page. You can do this in two ways :

* 1 <b>Redirect from success webpage.</b>
	The user will be prompted to show a success page with a button on it to navigate to the Login page.
    ```
    LOGIN_URL = 'name of your login pattern'

    Note: This variable is also used by Django.
    ```
* 2 <b>Redirect directly to the login page without stopping at the success message page.</b>
	The user will be directly sent to the login page, bypassing the success page.
    ```
    VERIFICATION_SUCCESS_TEMPLATE = None
    ```
</p>


> There is always room for improvements and new ideas, feel free to raise PR or Issues

### DRF Support
Using the latests commit(not yet published in the release of PyPi) you can easily adapt your view to support sending the verification!
```python
from verify_email.email_handler import _VerifyEmail

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    
    def perform_create(self, serializer):
        instance = serializer.save()
        # Send email for verification
        _VerifyEmail().send_verification_link(self.request, inactive_user=instance)
        instance.save()
```
