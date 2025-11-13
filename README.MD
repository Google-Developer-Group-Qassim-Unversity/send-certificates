# How to use this shit

### install dependencies
run 
```bash
pip install -r requirments.txt
```
to install all dependencies either globally or create a virtual envirnment.
or if you use `uv` just do `uv sync` then `uv run edit-pptx.py` which just works out of the box without the need for virtual envionments and shit.

### setup envionment varibles
there is a required envionemnt varible in the `.env` file that's called `APP_PASSWORD` you can find its value in notion under the page 'Certificate Mailing App'
this 'app password' is a 16-digit passcode that gives the script access the Google Account that is used to send emails from.
to get a fresh app password refer to this [google help page](https://support.google.com/mail/answer/185833?hl=en) under 'Create & use app passwords'

### How to use the script
There are a few varibles in the `edit-pptx.py` script which control what is written in the certificate.
There are 4 main varibles that can be found at the top of the file
* `EVENT_NAME` is for the event name which will be written in the certificate
* `ANNOUNCED_EVENT_NAME` This is in case the name on the certificate is different from what was announced, this will be sent in the email along side the certificate. in case the name donsn't differ just use the same name.
* `DATE` This is obivous, the date which is written on the certificate
* `DATA_URL` This a link to a google sheet of the members to be sent certificates to.
    it need to be 'published to web as csv' which you can do in sheets by `file`>`share`>`Publish to web` then choose a sheet and NOT 'entire documnet', change where it says Web Page to Comma-seperated-values, so that the data is published as csv.
    * 📝 Note that the sheet is not validated so you need to make sure that the data is clean and that there are no empty cells and that the columns names are correct
        the needed columns are `email` and `name` named exactly like that.
* `PRESENTATION_FILE_NAME` this is the `.pptx` file to be used as the certificate, right now there are 2 options `certificate.pptx` or `certificate unofficial.pptx`. and as you can see in the script one them is always commented out, just uncomment and comment depending on what type of certificate you need to send.

you don't need to change other varibles for script to work they are just for logging.

### Testing
if you want to test and see how the certificates and email will look you can use the `test()` function it takes a name and an email as arguments and will send a certificate based on the data you set in the varibles at the top of the file.
if you don't give it an email it will only generate the pdf file so that you can how it looks, and will not send an email
in the `if __name__ == '__main__'` block at the bottom of the script call `test()` instead of `main()` and run the file to test
the test functin will create a `.pptx` certificate and a `.pdf` version and will put it in the directory `test` as well as sending it you the email you gave it.

also the script is fairly verbos and will print what its doing as it does it.

### Which type of certificate to use?