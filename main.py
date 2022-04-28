import kivy
kivy.require('2.0.0')

import ast
import random
import certifi as cfi
from plyer import notification
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivy.network.urlrequest import UrlRequest
from kivy.utils import platform

patients = []
widgets = []
Builder.load_file('oximeterui.kv')

class Patient(BoxLayout):
	#these values will be sent by the arduino
	oxygen = NumericProperty()
	status = StringProperty('')
	battery = NumericProperty()

	#these are user inputs. can be changed whenever the user wants as long as Save is pressed
	name = StringProperty('')
	address = StringProperty('')

	def __init__(self):
		super().__init__()

		#scheduled to update the values in the screen
		Clock.schedule_interval(lambda dt:self.update(), 5)
		Clock.schedule_once(self.init_app)

	#initialize app object(to avoid potential errors)
	def init_app(self, *args):
		self.app = App.get_running_app()


	#some urlRequest functions
	def on_success(self,req,result):
		if result[0]['status'] == 'success': ## THIS IS NOT THE FINAL PARSER FOR REQUEST 
			self.oxygen = result[0]['random']
			if self.oxygen < 95:
				notification.notify(title="Alert",message=f"{self.name} is currently at {self.oxygen}%",timeout=10)
		self.status = 'Connected'

	def on_fail(self,req,result):
		self.status = 'Disconnected'
		print(req.result)

	def on_progress(self,req,result,chunk):
		self.status = "Connecting..."

	def on_error(self,req,error):
		print(error)
		self.status = "Reconnecting..."


	#update patient values
	def update(self):
		# url = "https://csrng.net/csrng/csrng.php?min=93&max=100"
		url = self.address
		if url:
			r = UrlRequest(url,on_success=self.on_success,on_progress=self.on_progress,on_failure=self.on_fail,on_error=self.on_error,ca_file=cfi.where(),verify=True)
			self.battery = random.randint(1,100)
			print("valid address")

	def save(self):
		self.name = self.ids.name.text
		self.address = self.ids.ipaddress.text

		if self.name:
			self.ids.name.disabled = True
			

		if self.address:
			self.ids.ipaddress.disabled = True

		if self not in patients:
			patients.append(self)
		if self.ids.patient_card not in widgets:
			widgets.append(self.ids.patient_card)


	#delete all widgets and redraw all except the one deleted
	def delete(self):
		if patients:
			patients.remove(self)

		self.remove_widget(self.ids.patient_card)

		self.app.root.ids.container.clear_widgets()
		for i in patients:
			self.app.root.ids.container.add_widget(i)

class AppLayout(Widget):

	def add_patient(self):
		new_patient = Patient()
		self.ids.container.add_widget(new_patient)
		patients.append(new_patient)

		if patients:
			self.ids.container.clear_widgets()
			for i in patients:
				self.ids.container.add_widget(i)


class OximeterApp(App):
	def build_config(self,config):
		config.setdefaults('patients',{'name':'[]','address':'[]'})

	def build(self):
		Window.bind(on_request_close=self.on_request_close)
		if platform == 'android':
			Window.borderless = 1
			Window.softinput_mode = "below_target"
			Window.keyboard_anim_args = {"d":0.2,"t":"linear"}
		else:
			Window.borderless = 0
			Window.size = (650,650)
		return AppLayout()

	def on_request_close(self, *args):
		self.textpopup(title='Exit', text='Are you sure?')
		return True

	def textpopup(self, title='', text=''):
		"""Open the pop-up with the name.
		:param title: title of the pop-up to open
		:type title: str
		:param text: main text of the pop-up to open
		:type text: str
		:rtype: None
		"""
		box = BoxLayout(orientation='vertical')
		box.add_widget(Label(text=text,color=(1,1,1,1)))
		mybutton = Button(text='Yes', size_hint=(1, 0.25),color = (1,1,1,1))
		box.add_widget(mybutton)
		popup = Popup(title=title, content=box, size_hint=(0.5,0.3))
		mybutton.bind(on_release=self.stop)
		popup.open()

	def save_config(self):
		names = []
		addresses = []

		for i in self.root.ids.container.children:
			names.append(i.name)
			addresses.append(i.address)

		names.reverse()
		addresses.reverse()

		# set the data in the config
		self.config.set('patients', 'name', str(names))
		self.config.set('patients', 'address', str(addresses))

		# write the config file
		self.config.write()

	def load_my_config(self):
		# extract saved data from the config
		names_str = self.config.get('patients', 'name')
		addresses_str = self.config.get('patients', 'address')

		# use the extracted data to build the Labels
		names = ast.literal_eval(names_str)
		addresses = ast.literal_eval(addresses_str)

		#add patient cards from previous session
		for name,address in zip(names,addresses):
			patient = Patient() #create new Patient object
			#set properties according to saved data
			patient.name = name
			patient.address = address
			self.root.ids.container.add_widget(patient)
			patient.save() #Save the current object to patients list

	def on_stop(self):
		self.save_config()

	def on_start(self):
		self.load_my_config()

	def on_pause(self):
		self.save_config()
		return True


if __name__ in ("__main__","__android__"):
	OximeterApp().run()
