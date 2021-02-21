#!/usr/bin/env python
'''
The barman.

This is a simple script for use on a Raspberry Pi to drive my mini cocktail
maker. That maker drives a bunch of
  INTLLAB 12V DC DIY Peristaltic Liquid Pump Dosing Pumps
using a
  Kootek 8 Channel DC 5V Relay Module
hooked up to the GPIO pins. The screen is the standard
  Pi Foundation Display - 7" Touchscreen Display
but other touchscreens should probably work. (I had to muck about a little
to make Kivy play nice with that screen if I recall.)
'''

from __future__ import print_function, division

from espeak              import espeak
from kivy.app            import App
from kivy.config         import Config
from kivy.core.window    import Window
from kivy.uix.button     import Button
from kivy.uix.boxlayout  import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label      import Label
from kivy.clock          import Clock
from kivy.graphics       import Color, Rectangle
from threading           import Thread
from time                import sleep, time

import RPi.GPIO as GPIO
import argh
import numpy

# ----------------------------------------------------------------------

# Hardware constants.

# The GPIO pins (BCM mapping)
_PINS = (27, 17, 18, 15, 14, 4, 3, 2)

# The flow rate of each pump, in millilitres per second. Constants computed by
# timing how long it took to pump X mls...
_MLS_PER_SEC = (100.0 / 55.0,
                100.0 / 56.0,
                100.0 / 60.0,
                100.0 / 62.0,
                100.0 / 55.0,
                100.0 / 57.0,
                100.0 / 55.0,
                100.0 / 63.0)

# ----------------------------------------------------------------------

# Software constants.

# The known ingredients
_ABSINTHE            = "Absinthe"
_AMARETTO            = "Amaretto"
_APEROL              = "Aperol"
_APRICOT_BRANDY      = "Apricot Brandy"
_BACARDI             = "Bacardi Carta Blanca"
_BAILEYS             = "Baileys Irish Cream"
_BLACKBERRY_LIQUEUR  = "Blackberry Liqueur"
_BOURBON             = "Bourbon"
_BRANDY              = "Brandy"
_CALVADOS            = "Calvados"
_CAMPARI             = "Campari"
_CHAMPAGNE           = "Champagne"
_CHERRY_LIQUEUR      = "Cherry Liqueur"
_CITRON_VODKA        = "Citron Vodka"
_COCONUT_CREAM       = "Coconut Cream"
_COFFEE_LIQUEUR      = "Coffee Liqueur"
_COGNAC              = "Cognac"
_COINTREAU           = "Cointreau"
_COLA                = "Cola"
_CRANBERRY_JUICE     = "Cranberry Juice"
_CREAM               = "Cream"
_CREME_DE_CACAO      = "Creme De Cacao"
_CREME_DE_CASSIS     = "Creme De Cassis"
_CREME_DE_MENTHE     = "Creme De Menthe"
_DARK_RUM            = "Dark Rum"
_DOM_BENEDICTINE     = "Dom Benedictine"
_DRAMBUIE            = "Drambuie"
_DRY_VERMOUTH        = "Dry Vermouth"
_DRY_WHITE_WINE      = "Dry White Wine"
_ESPRESSO            = "Espresso"
_GALLIANO            = "Galliano"
_GIN                 = "Gin"
_GINGER_ALE          = "Ginger Ale"
_GINGER_BEER         = "Ginger Beer"
_GOMME_SYRUP         = "Gomme Syrup"
_GRAND_MARNIER       = "Grand Marnier"
_GRAPEFRUIT_JUICE    = "Grapefruit Juice"
_GRENADINE           = "Grenadine"
_KAHLUA              = "Kahlua"
_KIRSCH              = "Kirsch"
_LEMON_JUICE         = "Lemon Juice"
_LILLET_BLONDE       = "Lillet Blonde"
_LIME_JUICE          = "Lime Juice"
_MARASCHINO          = "Maraschino"
_OLD_TOM_GIN         = "Old Tom Gin"
_OLIVE_JUICE         = "Olive Juice"
_ORANGE_CURACAO      = "Orange Curacao"
_ORANGE_FLOWER_WATER = "Orange Flower Water"
_ORANGE_JUICE        = "Orange Juice"
_ORGEAT_SYRUP        = "Orgeat Syrup"
_PEACH_PUREE         = "Peach Puree"
_PEACH_SCHNAPPS      = "Peach Schnapps"
_PINEAPPLE_JUICE     = "Pineapple Juice"
_PISCO               = "Pisco"
_PROSECCO            = "Prosecco"
_RASPBERRY_LIQUEUR   = "Raspberry Liqueur"
_RASPBERRY_SYRUP     = "Raspberry Syrup"
_RED_VERMOUTH        = "Red Vermouth"
_RYE                 = "Rye Whisky"
_SCOTCH              = "Scotch Whiskey"
_SIMPLE_SYRUP        = "Simple Syrup"
_SODA_WATER          = "Soda Water"
_SUGAR_SYRUP         = "Sugar Syrup"
_TEQUILA             = "Tequila"
_TOMATO_JUICE        = "Tomato Juice"
_TRIPLE_SEC          = "Triple Sec"
_VANILLA_EXTRACT     = "Vanilla Extract"
_VODKA               = "Vodka"
_VODKA_CITRON        = "Vodka Citron"
_WHITE_RUM           = "White Rum"

# Our known cocktails. Name maps to a tuple of (millilitres, ingredient).
_COCKTAILS = {
    "BELLINI" : (
        ((100, _PROSECCO),
         ( 50, _PEACH_PUREE),),
        ''
    ),
    "BLACK RUSSIAN" : (
        ((50, _VODKA),
         (20, _COFFEE_LIQUEUR),),
        ''
    ),
    "BLOODY MARY" : (
        ((45, _VODKA),
         (90, _TOMATO_JUICE),
         (15, _LEMON_JUICE),),
        'Add Worcestershire Sauce, Tabasco, Celery Salt, and Pepper'
    ),
    "CHAMPAGNE COCKTAIL" : (
        ((90, _CHAMPAGNE),
         (10, _COGNAC),),
        'Add 2 dashes of Angostura Bitters and a sugar cube'
    ),
    "COSMOPOLITAN" : (
        ((40, _CITRON_VODKA),
         (15, _COINTREAU),
         (30, _CRANBERRY_JUICE),
         (15, _LIME_JUICE),),
        ''
    ),
    "CUBA LIBRE" : (
        (( 50, _WHITE_RUM),
         (120, _COLA),
         ( 10, _LIME_JUICE),),
        ''
    ),
    "FRENCH 75" : (
        ((30, _GIN),
         (15, _LEMON_JUICE),
         (60, _CHAMPAGNE),),
        'Add 2 dashes of sugar syrup'
    ),
    "FRENCH CONNECTION" : (
        ((35, _COGNAC),
         (35, _AMARETTO),),
        ''
    ),
    "GOD FATHER" : (
        ((35, _SCOTCH),
         (35, _AMARETTO),),
        ''
    ),
    "GOD MOTHER" : (
        ((35, _VODKA),
         (35, _AMARETTO),),
        ''
    ),
    "GOLDEN DREAM" : (
        ((20, _GALLIANO),
         (20, _TRIPLE_SEC),
         (20, _ORANGE_JUICE),),
        'Add a little cream'
    ),
    "GRASSHOPPER" : (
        ((30, _CREME_DE_CACAO),
         (30, _CREME_DE_MENTHE),),
        'Add 30 ml of cream'
    ),
    "HARVEY WALLBANGER" : (
        ((45, _VODKA),
         (90, _ORANGE_JUICE),
         (15, _GALLIANO),),
        'Add a cherry'
    ),
    "HEMINGWAY SPECIAL" : (
        ((60, _WHITE_RUM),
         (15, _MARASCHINO),
         (40, _GRAPEFRUIT_JUICE),
         (15, _LIME_JUICE),),
        ''
    ),
    "HORSE'S NECK" : (
        (( 40, _BRANDY),
         (120, _GINGER_ALE),),
        'Add bitters'
    ),
    "KIR" : (
        ((90, _DRY_WHITE_WINE),
         (10, _CREME_DE_CASSIS),),
        ''
    ),
    "LONG ISLAND ICED TEA" : (
        ((15, _GIN),
         (15, _TEQUILA),
         (15, _VODKA),
         (15, _WHITE_RUM),
         (15, _TRIPLE_SEC),
         (25, _LEMON_JUICE),),
        'Add 2 dashes of cola, and 1 of gomme syrup'
    ),
    "MAI-TAI" : (
        ((40, _WHITE_RUM),
         (20, _DARK_RUM),
         (15, _ORANGE_CURACAO),
         (15, _ORGEAT_SYRUP),
         (10, _LIME_JUICE),),
        ''
    ),
    "MARGARITA" : (
        ((35, _TEQUILA),
         (20, _COINTREAU),
         (15, _LIME_JUICE),),
        ''
    ),
    "MIMOSA" : (
        ((75, _CHAMPAGNE),
         (75, _ORANGE_JUICE),),
        ''
    ),
    "MOJITO" : (
        (( 40, _WHITE_RUM),
         ( 30, _LIME_JUICE),
         (100, _SODA_WATER),),
        ''
    ),
    "MOSCOW MULE" : (
        (( 45, _VODKA),
         (120, _GINGER_BEER)),
        'Add 2 dashes of lime juice'
    ),
    "PINA COLADA" : (
        ((30, _WHITE_RUM),
         (90, _PINEAPPLE_JUICE),
         (30, _COCONUT_CREAM),),
        ''
    ),
    "ROSE" : (
        ((20, _KIRSCH),
         (40, _DRY_VERMOUTH),),
        'Add strawberry syrup'
    ),
    "SEA BREEZE" : (
        (( 40, _VODKA),
         (120, _CRANBERRY_JUICE),
         ( 30, _GRAPEFRUIT_JUICE),),
        ''
    ),
    "SEX ON THE BEACH" : (
        ((40, _VODKA),
         (20, _PEACH_SCHNAPPS),
         (40, _CRANBERRY_JUICE),
         (40, _ORANGE_JUICE),),
        ''
    ),
    "SINGAPORE SLING" : (
        (( 30, _GIN),
         ( 15, _CHERRY_LIQUEUR),
         (  7, _COINTREAU),
         (  7, _DOM_BENEDICTINE),
         ( 10, _GRENADINE),
         (120, _PINEAPPLE_JUICE),
         ( 15, _LIME_JUICE),),
        'Add bitters'
    ),
    "TEQUILA SUNRISE" : (
        ((45, _TEQUILA),
         (90, _ORANGE_JUICE),
         (15, _GRENADINE),),
        ''
    ),
    "B52" : (
        ((20, _GRAND_MARNIER),
         (20, _BAILEYS),
         (20, _KAHLUA),),
        ''
    ),
    "BARRACUDA" : (
        ((45, _WHITE_RUM),
         (15, _GALLIANO),
         (60, _PINEAPPLE_JUICE),),
        'Top off with a dash of lime and Prosecco'
    ),
    "BRAMBLE" : (
        ((40, _GIN),
         (15, _LEMON_JUICE),),
        'Add 4 dashes of sugar syrup and 1 of blackberry liqueur'
    ),
    "DARK 'N' STORMY" : (
        (( 60, _DARK_RUM),
         (100, _GINGER_BEER),),
        ''
    ),
    "DIRTY MARTINI" : (
        ((60, _VODKA),
         (10, _DRY_VERMOUTH),
         (10, _OLIVE_JUICE),),
        ''
    ),
    "ESPRESSO MARTINI" : (
        ((50, _VODKA),
         (10, _KAHLUA),
         (20, _ESPRESSO),),
        ''
    ),
    "FRENCH MARTINI" : (
        ((45, _VODKA),
         (15, _RASPBERRY_LIQUEUR),
         (15, _PINEAPPLE_JUICE),),
        ''
    ),
    "KAMIKAZE" : (
        ((30, _VODKA),
         (30, _TRIPLE_SEC),
         (30, _LIME_JUICE),),
        ''
    ),
    "LEMON DROP MARTINI" : (
        ((25, _VODKA),
         (20, _TRIPLE_SEC),
         (15, _LEMON_JUICE),),
        ''
    ),
    "PISCO SOUR" : (
        ((45, _PISCO),
         (30, _LEMON_JUICE),),
        'Add egg white and suagr syrup'
    ),
    "RUSSIAN SPRING PUNCH" : (
        ((25, _VODKA),
         (15, _CREME_DE_CASSIS),
         (25, _LEMON_JUICE),),
        'Add 4 dashes of sugar syrup'
    ),
    "SPRITZ VENEZIANO" : (
        ((60, _PROSECCO),
         (40, _APEROL),),
        'Add a splash of soda water'
    ),
    "TOMMY'S MARGARITA" : (
        ((45, _TEQUILA),
         (15, _LIME_JUICE),),
        'Add 2 teaspoons of Agave nectar'
    ),
    "VESPER" : (
        ((60, _GIN),
         (15, _VODKA),),
        'Add a dash of Lillet Blonde/Blanc'
    ),
    "YELLOW BIRD" : (
        ((30, _WHITE_RUM),
         (15, _GALLIANO),
         (15, _TRIPLE_SEC),
         (15, _LIME_JUICE),),
        ''
    ),
    "ALEXANDER" : (
        ((30, _COGNAC),
         (30, _CREME_DE_CACAO),
         (30, _CREAM),),
        ''
    ),
    "AMERICANO" : (
        ((30, _CAMPARI),
         (30, _RED_VERMOUTH),
         (20, _SODA_WATER),),
        ''
    ),
    "ANGEL FACE" : (
        ((30, _CALVADOS),
         (30, _GIN),
         (30, _APRICOT_BRANDY),),
        ''
    ),
    "AVIATION" : (
        ((45, _GIN),
         (15, _MARASCHINO),
         (15, _LEMON_JUICE),),
        ''
    ),
    "BACARDI" : (
        ((45, _BACARDI),
         (20, _LIME_JUICE),
         (10, _GRENADINE),),
        ''
    ),
    "BETWEEN THE SHEETS" : (
        ((30, _COGNAC),
         (30, _WHITE_RUM),
         (30, _TRIPLE_SEC),
         (20, _LEMON_JUICE),),
        ''
    ),
    "CASINO" : (
        ((40, _OLD_TOM_GIN),
         (10, _MARASCHINO),
         (10, _LEMON_JUICE),),
        ''
    ),
    "CLOVERCLUB" : (
        ((45, _GIN),
         (15, _LEMON_JUICE),),
        'Add raspberry syrup and a few drops of egg white'
    ),
    "DAIQUIRI" : (
        ((45, _WHITE_RUM),
         (15, _SIMPLE_SYRUP),
         (25, _LIME_JUICE),),
        ''
    ),
    "DRY MARTINI" : (
        ((60, _GIN),
         (10, _DRY_VERMOUTH),),
        ''
    ),
    "GIN FIZZ" : (
        ((45, _GIN),
         (30, _LEMON_JUICE),
         (80, _SODA_WATER),),
        'Add a dash of suagr syrup'
    ),
    "JOHN COLLINS" : (
        ((45, _GIN),
         (30, _LEMON_JUICE),
         (60, _SODA_WATER),),
        'Add 4 dashes of sugar syrup'
    ),
    "MANHATTAN" : (
        ((50, _RYE),
         (20, _RED_VERMOUTH),),
        'Add bitters'
    ),
    "MARY PICKFORD" : (
        ((60, _WHITE_RUM),
         (10, _MARASCHINO),
         (10, _GRENADINE),
         (60, _PINEAPPLE_JUICE),),
        ''
    ),
    "MONKEY GLAND" : (
        ((50, _GIN),
         (30, _ORANGE_JUICE),),
        'Add 2 drops of Absinthe and 2 dashes of Grenadine'
    ),
    "NEGRONI" : (
        ((30, _GIN),
         (30, _CAMPARI),
         (30, _RED_VERMOUTH),),
        ''
    ),
    "PARADISE" : (
        ((35, _GIN),
         (20, _APRICOT_BRANDY),
         (15, _ORANGE_JUICE),),
        ''
    ),
    "PLANTER'S PUNCH" : (
        ((45, _DARK_RUM),
         (35, _ORANGE_JUICE),
         (35, _PINEAPPLE_JUICE),
         (20, _LEMON_JUICE),),
        'Add 2 dashes each of grenadine and sugar syrup'
    ),
    "RUSTY NAIL" : (
        ((45, _SCOTCH),
         (25, _DRAMBUIE),),
        ''
    ),
    "SAZERAC" : (
        ((50, _COGNAC),),
        'Add 4 dashes of Absinthe, 1 of bitters, and a sugar cube'
    ),
    "SCREWDRIVER" : (
        (( 50, _VODKA),
         (100, _ORANGE_JUICE),),
        ''
    ),
    "SIDECAR" : (
        ((50, _COGNAC),
         (20, _TRIPLE_SEC),
         (20, _LEMON_JUICE),),
        ''
    ),
    "STINGER" : (
        ((50, _COGNAC),
         (20, _CREME_DE_MENTHE),),
        ''
    ),
    "TUXEDO" : (
        ((30, _OLD_TOM_GIN),
         (30, _DRY_VERMOUTH),),
        'Add 2 dashes of Maraschino, 1 dash of Absinthe and 3 dashes of bitters'
    ),
    "WHISKEY SOUR" : (
        ((45, _BOURBON),
         (30, _LEMON_JUICE),),
        'Add 4 dashes of sugar syrup'
    ),
    "WHITE LADY" : (
        ((40, _GIN),
         (30, _TRIPLE_SEC),
         (20, _LEMON_JUICE),),
        ''
    ),
    "FOGHORN" : (
        ((30, _GIN),
         (60, _GINGER_BEER),),
        ''
    ),
}

# ======================================================================

def stop():
    '''
    Stop the pumps.
    '''
    for pin in _PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, True)


def validate_ingredients(ingredients):
    '''
    Check that the ingredients look right.
    '''
    # Make sure we have the right number, since they need to map to the GPIO
    # pins
    assert len(ingredients) == 8, (
        "Expected 8 ingredients but had %d: %s" %
        (len(ingredients), ", ".join(ingredients))
    )

    # Make sure that we know them
    known = set()
    for cocktail in sorted(_COCKTAILS.keys()):
        (quantities, extras) = _COCKTAILS[cocktail]
        for (millilitres, drink) in quantities:
            known.add(drink)
    for ingredient in ingredients:
        if ingredient != '' and ingredient not in known:
            raise ValueError("Unknown ingredient: \"%s\"" % ingredient)


def compute_cocktails(ingredients):
    '''
    Given a list of ingredients, keyed by pump index, compute the list available
    cocktail names.
    '''
    # Sanity check the ingredients, always
    validate_ingredients(ingredients)

    # The list of available cocktails which we'll return
    result = list()

    # Walk the cocktails and see if we have all the ingredients for them
    for (name, details) in _COCKTAILS.iteritems():
        (quantities, extras) = details
        if numpy.all([
            ingredient in ingredients
                for (quantity, ingredient) in quantities
        ]):
            result.append(name)

    # And give back the list
    return result
    
    
# ----------------------------------------------------------------------

class Barman(App):
    def __init__(self, ingredients, scale=1.0):
        '''
        CTOR with the known ingredients.
        '''
        super(Barman, self).__init__()

        # Talk a little slower and differenter
        espeak.set_parameter(espeak.Parameter.Rate, 100)
        espeak.set_voice('english-north')

        if False:
            Window.fullscreen = True
        else:
            #Config.set('graphics', 'width',  '800')
            #Config.set('graphics', 'height', '460')
            Config.set('graphics', 'borderless',       1)
            Config.set('graphics', 'fullscreen',  'auto')
            Config.set('graphics', 'show_cursor',      0)
            Config.write()

        # Remember these
        self._ingredients = ingredients
        self._scale       = scale
        self._label       = None
        self._off_calls   = 0

        # Set up GPIO
        self.off()

        # Say what we got
        cocktails = compute_cocktails(ingredients)
        if len(cocktails) == 0:
            raise ValueError("No cocktails for those ingredients")
        else:
            self.info("Available drinks are: %s." %
                      (", ".join(cocktails)))
        

    def build(self):
        '''
        Set up the GUI, given the list of ingredients.
        '''
        # Set up the basic canvas etc,
        layout = BoxLayout(orientation='vertical')
        grid   = GridLayout(cols=3)
        self._label = Label()

        # How the button will make the drink
        def make_mix(name):
            return lambda obj: self.mix(name, self._ingredients)
        def make_straight(name):
            return lambda obj: self.straight(name, self._ingredients)

        # Add buttons for all drinks
        for name in compute_cocktails(self._ingredients):
            button = Button(text=name)
            button.bind(on_press=make_mix(name))
            grid.add_widget(button)

        # And for the ingredients on their own;
        for (index, name) in enumerate(self._ingredients):
            if name != '':
                button = Button(text=name)
                button.bind(on_press=make_straight(name))
                grid.add_widget(button)

        # And add an off button, just in case!
        stop = Button(text="STOP!", background_color=(1,0,0,1))
        stop.bind(on_press=lambda obj: self.off())

        # And add everything
        info = BoxLayout(orientation='vertical')
        info.add_widget(self._label)
        info.add_widget(stop)
        layout.add_widget(grid)
        layout.add_widget(info)

        # We're done! Call off to init the pumps and say we're ready to serve.
        self.info("Ready to serve!")
        return layout


    def info(self, message):
        '''
        Print a message.
        '''
        espeak.synth(message)
        print(message)
        if self._label is not None:
            self._label.text = message

    # Functions which control the hardware.
    
    def off(self):
        '''
        Turn off all the pumps and clear texts.
        '''
        # Shut up
        if self._label is not None:
            self._label.text = ""
        espeak.cancel()

        # Turn off pumps
        stop()

        # We were called
        self._off_calls += 1
    
    
    def pump(self, index, millis):
        '''
        Pump the given amount of millilitres out from the given pump index.
        '''
        # What we're pumping and for how long
        pin     = _PINS       [index]
        rate    = _MLS_PER_SEC[index]
        seconds = max(0.0, min(100.0, millis)) / rate
    
        # Pump until the right number of seconds has passed
        off_calls = self._off_calls
        try:
            print("Pumping %d for %0.1fs" % (index, seconds))
            start = time()
            GPIO.output(pin, False)
            while (time() - start) < seconds:
                if off_calls != self._off_calls:
                    return
                else:
                    sleep(0.1)
            print("Pumped %d for %0.1fs" % (index, time() - start))

        finally:
            # When we get here, for whatever reason, turn off the pump. We really
            # don't want to leave it on...
            if off_calls == self._off_calls:
                GPIO.output(pin, True)
    
    # ----------------------------------------------------------------------
    
    # Cocktail functions.
    
    def mix(self, name, ingredients):
        '''
        Given a cocktail name, mix one for me!
        '''
        # Turn everything off first, we're starting fresh
        self.off()
    
        # Get the cocktail recipe
        try:
            details = _COCKTAILS[name]
        except KeyError:
            raise ValueError("Unknown cocktail: %s " % (name,))
        (recipe, extras) = details
    
        # Check that we have what we need.
        wants = "%s" % (name,)
        pump_list = list()
        for (millilitres, ingredient) in recipe:
            if ingredient not in ingredients:
                raise ValueError("Missing %s" % ingredient)
            else:
                wants += ",\n  %d ml %s" % (millilitres, ingredient)
                pump_list.append((ingredients.index(ingredient), millilitres))
        wants += "."
        self.info(wants)
    
        # Create a thread for each pump so that we can run
        def make_thread(index, millilitres):
            return Thread(target = lambda: self.pump(index, millilitres))
        threads = list()
        for (index, millilitres) in pump_list:
            threads.append(make_thread(index, millilitres * self._scale))
    
        # Start all the threads and we're done; we return control to the GUI
        for thread in threads:
            thread.start()

        # Wait for the drink to be mixed
        def wait(off_calls):
            for thread in threads:
                thread.join()
            if off_calls == self._off_calls:
                if extras == '':
                    self.info("Drink is ready!")
                else:
                    self.info(extras)
        Thread(target=lambda: wait(self._off_calls)).start()


    def straight(self, name, ingredients):
        '''
        Given a cocktail name, mix one for me!
        '''
        # Turn everything off first, we're starting fresh
        self.off()
    
        # What we're doing
        index       = ingredients.index(name)
        millilitres = 10
    
        # Check that we have what we need.
        self.info("%d ml %s" % (millilitres, name))
    
        # Create a thread for each pump so that we can run
        def make_thread(index, millilitres):
            return Thread(target = lambda: self.pump(index, millilitres))
        thread = make_thread(index, millilitres)
        thread.start()
    
        # Wait for the drink to be mixed
        def wait(off_calls):
            thread.join()
            if off_calls == self._off_calls:
                self.info("Drink is ready!")
        Thread(target=lambda: wait(self._off_calls)).start()

# ----------------------------------------------------------------------

def flush():
    try:
        for pin in _PINS:
            GPIO.output(pin, False)
        sleep(15)
    finally:
        for pin in _PINS:
            GPIO.output(pin, True)

def ingredients():
    '''
    List all the known drinks to use for ingredients.
    '''
    drinks = list()
    for details in _COCKTAILS.values():
        (quantities, extras) = details
        for (millilitres, drink) in quantities:
            drinks.append(drink)

    print("Main ingredients by number of cocktails:")
    for drink in sorted(set(drinks)):
        print("%3s  %s" % (drinks.count(drink), drink))


def drinks():
    '''
    List all the known cocktails and their ingredients.
    '''
    for cocktail in sorted(_COCKTAILS.keys()):
        print("%s:" % cocktail)
        (quantities, extras) = _COCKTAILS[cocktail]
        for (millilitres, drink) in quantities:
            print("    %s" % drink)
        if extras != '':
            print("  %s" % extras)


def available(*args):
    '''
    Given the list of drinks, print out what we can make.
    '''
    # Pad out the list to 8
    ingredients = list(args)
    while len(ingredients) < 8:
        ingredients.append('')

    # Make sure that we don't have too many
    if len(ingredients) > 8:
        raise ValueError("Too many ingredients: %s" % ", ".join(ingredients))

    # And compute
    cocktails = compute_cocktails(ingredients)
    if len(cocktails) == 0:
        print("No cocktails for that list")
    else:
        print("Available drinks are:")
        for name in cocktails:
            (quantities, extras) = _COCKTAILS[name]
            print("  %-25s %s" % (name, extras))


@argh.arg('--scale',
          default=1.0,
          help='Scale the recipes by this floating point factor')
def run(*args, scale=1.0):
    '''
    Set the barman in action.
    '''
    barman = Barman(args, scale=scale)
    barman.run()

# ======================================================================

if __name__ == "__main__":
    # Set up the GPIO before we do anything else
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    stop()

    # And hand off
    try:
        argh.dispatch_commands([flush, ingredients, drinks, available, run])
    except Exception as e:
        print("%s" % e)
