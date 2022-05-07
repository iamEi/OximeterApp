import kivy
kivy.require('2.0.0')

import ast
import time
import random
import threading
import certifi as cfi
from bs4 import BeautifulSoup
from datetime import datetime
from plyer import notification
from kivymd.app import MDApp
from kivymd.toast import toast
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.utils import platform
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivy.network.urlrequest import UrlRequest
from kivy.core.clipboard import Clipboard
from kivy.storage.jsonstore import JsonStore
try:
	import pyi_splash
	pyi_splash.close()
except Exception:
	pass

TESTING = False #SET TO TRUE IF PROGRAM IS IN TESTING PHASE 
ANDROID = 1 if platform == 'android' else None

patients = []
Builder.load_file('oxymapp_ui.kv')
db = JsonStore('oxymapp_db.json')

class Patient(BoxLayout):
	#these values will be sent by the arduino
	oxygen = NumericProperty()
	status = StringProperty('Not Connected')
	battery = NumericProperty()
	pulse = NumericProperty()

	#these are user inputs. can be changed whenever the user wants as long as Save is pressed
	name = StringProperty('')
	address = StringProperty('')

	#if FALSE, the system will not trigger HTTP REQUEST. 
	#User must press 'Save' to start requesting from server
	saved = False

	def __init__(self):
		super().__init__()
		#scheduled to update the values in the screen
		Clock.schedule_interval(lambda dt:self.update(), 2)
		Clock.schedule_once(self.init_app)

	#initialize app object(to access widgets from another class)
	def init_app(self, *args):
		self.app = MDApp.get_running_app()

	def notify(self):
		notification.notify(
				title="Alert",
				message=f"{self.name} is currently at {self.oxygen}%",
				timeout=10
				)


	#some urlRequest functions
	def on_success(self,req,result):
		#Extract Value from HTML
		b4 = BeautifulSoup(result,"html.parser")
		webpage = b4.body.table
		oxygen_val = webpage.find(id="spo2").text
		pulse_val = webpage.find(id="heartrate").text

		self.oxygen = int(oxygen_val)
		self.pulse = int(pulse_val)
		if 100 < self.oxygen or self.oxygen < 95:
			self.app.run_on_thread(self.notify)
		self.status = 'Connected'
		self.battery = 100

	def on_fail(self,req,result):
		self.status = 'Disconnected'

	def on_progress(self,req,result,chunk):
		self.status = "Connecting..."

	def on_error(self,req,error):
		self.saved = False
		self.status = "Not Connected"
		self.battery = 0
		toast(f"Couldn't Connect to {self.address}\nCheck and Save Again")
		
	#update patient values
	def update(self):
		if self.saved:
			if self.address:
				url = "http://"+self.address if self.address[:3].isdigit() else self.address
				r = UrlRequest(
					url,
					on_success=self.on_success,
					on_progress=self.on_progress,
					on_failure=self.on_fail,
					on_error=self.on_error,
					ca_file=cfi.where(),
					verify=True)
		#For Testing Purpposes
		if TESTING:
			self.oxygen = random.randint(94,100)
			self.battery = random.randint(1,100) 
			self.pulse = random.randint(50,100)

	def save(self):
		self.saved = True

		self.name = self.ids.name.text
		self.address = self.ids.ipaddress.text

		if self.name:
			self.ids.name.disabled = True
			
		if self.address:
			self.ids.ipaddress.disabled = True

		if self not in patients:
			patients.append(self)


		self.status = 'Connecting...'
		toast('Saved!')

	def clear_name(self):
		self.name = ""
		self.ids.name.text = ""

	def clear_address(self):
		self.address = ""
		self.ids.ipaddress.text = ""

	def disable_name(self):
		self.ids.name.disabled = False

	def disable_address(self):
		self.ids.ipaddress.disabled = False

	def paste_name(self):
		self.ids.name.text = Clipboard.paste()

	def paste_address(self):
		self.ids.ipaddress.text = Clipboard.paste()


	#delete all widgets and redraw all except the one deleted
	def delete(self):
		self.saved = False
		if patients:
			patients.remove(self)

		self.remove_widget(self.ids.patient_card)

		self.app.root.ids.container.clear_widgets()
		for i in patients:
			self.app.root.ids.container.add_widget(i)
		
		toast('Delete Successful')

class AppLayout(Widget):

	def add_patient(self):
		new_patient = Patient()
		self.ids.container.add_widget(new_patient)
		patients.append(new_patient)

		if patients:
			self.ids.container.clear_widgets()
			for i in patients:
				self.ids.container.add_widget(i)


class OxymappApp(MDApp):
	def build_config(self,config):
		config.setdefaults('patients',{'name':'[]','address':'[]'})

	def build(self):
		self.icon = "img/icon.png"
		Window.bind(on_keyboard=self.my_key_handler)
		Window.bind(on_request_close=self.on_request_close)
		Clock.schedule_interval(lambda dt:self.run_on_thread(self.store),60)

		if ANDROID:
			Window.borderless = 1
			Window.keyboard_anim_args = {"d":0.2,"t":"in_out_expo"}
			Window.softinput_mode = "below_target"
		else:
			Window.borderless = 0
			Window.size = (650,650)
		return AppLayout()

	def run_on_thread(self,target):
		t1 = threading.Thread(target=target)
		t1.start()

	def store(self):
		for i in patients:
			if i.saved:
				now = datetime.now()
				date_time = now.strftime("%m/%d/%Y - %H:%M:%S || ")
				db.put(
					date_time,
					status=i.status,
					name=i.name,
					oxygen=str(i.oxygen))
				time.sleep(1)

	def my_key_handler(self, window, keycode1, keycode2, text, modifiers):
		# this is esc key on desktop or back button on android
		if keycode1 in [27, 1001]:
			# call your popup here
			self.exitpopup(title='Exit', text='Are you sure?')
			return True

	#Override the F1 button to show Logs instead of Settings
	def open_settings(self, *largs):
		self.show_logs()

	def on_request_close(self, *args):
		self.exitpopup(title='Exit', text='Are you sure?')
		return True

	def exitpopup(self, title='', text=''):
		box = BoxLayout(orientation='vertical')
		box.add_widget(Label(text=text,color=(1,1,1,1)))

		mybutton = Button(
			text='Yes',
			size_hint=(0.5, 0.25),
			pos_hint={"center_x":0.5},
			color = (1,1,1,1),
			background_color=(1,0,0,0.5))
		box.add_widget(mybutton)

		popup = Popup(title=title, content=box, size_hint=(0.5,0.3))
		mybutton.bind(on_release=self.stop)
		popup.open()

	def clear_popup(self, *args):
		if db:
			box = BoxLayout(orientation='vertical')
			box.add_widget(Label(text='Proceed?',color=(1,1,1,1)))
			Yes = Button(
				text='Yes',
				size_hint=(0.4, 1),
				color = (1,1,1,1),
				background_color=(1,0,0,0.5))
			No = Button(
				text='No',
				size_hint=(0.4, 1),
				color = (1,1,1,1),
				background_color=(1,0,0,0.5))
			buttons = GridLayout(
				cols=2,spacing=5,
				size_hint=(1,0.25))

			buttons.add_widget(Yes)
			buttons.add_widget(No)
			box.add_widget(buttons)
			popup = Popup(title='Delete All Logs',content=box,size_hint=(0.5,0.3))
			Yes.bind(on_press=self.clear_logs)
			Yes.bind(on_release=popup.dismiss)
			No.bind(on_release=popup.dismiss)
			popup.open()
		else:
			toast('Nothing to Clear')

	def clear_logs(self, *args):
		db.clear()
		toast("Logs Cleared!")

	def show_logs(self):
		container =  BoxLayout(orientation='vertical')

		view = ScrollView(
			size_hint=(1,0.9),
			do_scroll_y = True)	

		box = GridLayout(
			cols=1,
			size_hint_y=None,
			spacing=10,
			height=0
			)

		container.add_widget(view)
		view.add_widget(box)

		templist = []
		for key in db.keys():
			name = db.get(key)['name']
			if name not in templist:
				templist.insert(0,name)

		for i in templist:
			logs=""
			name_ = ""
			for item in db.find(name=i):
				name_ = item[1]['name']
				logs += f"{item[0]} SpO2 = {item[1]['oxygen']}%\n"
			text = f"{name_}\n{logs}"
			label = Label(text=text,color=(1,1,1,1))
			label._label.refresh()
			label.height = label._label.texture.size[1]
			box.height += label.height
			box.add_widget(label)

		popup_size = (0.8,0.6) if ANDROID else (0.7,0.8)
		popup = Popup(
			title="Logs",
			content=container,
			size_hint=popup_size)
		container.add_widget(
			Button(
				text="Clear",
				color=(1,1,1,1),
				background_color=(1,0,0,0.5),
				size_hint=(0.2,0.1),
				pos_hint={"center_x":0.5},
				on_press=self.clear_popup,
				on_release=popup.dismiss))
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
	OxymappApp().run()
