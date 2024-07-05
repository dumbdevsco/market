import urllib.parse
import urllib.request
import requests
from bs4 import BeautifulSoup
import re
import datetime
import csv
import os


URL_ROOT = 'https://www.perekrestok.ru'


CARD_KEYS = ['name', 'price', 'size', 'url', 'time', 'name_', 'price_', 'brand', 'calories', 'proteins', 'fats', 'carbos', 'composition', 'get_ok', 'parse_ok', 'time_']

class Scrapper:
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5', 
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Cookie': '',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Priority': 'u=1',
        'TE': 'trailers'
    }

    max_cards = 0
    verbose = True
    write = True
    append = True
    
    dname = '../tsv/perekr'
    fext = '.tsv'
    delim = '\t'
    placeholder = 'none'

    file = None

    def __init__(self):
        pass

    def __del__(self):
        self.close_file()
        pass

    def run_shortcards(self, cat):
        self.close_file()
        scards = self.request_scards(cat)
        if self.write and self.append:
            urls_file = self.read_urls_csv(self.get_file(cat))
            urls = [item['url'] for item in scards]
            urls = list(set(urls).difference(urls_file))
            scards = list(filter(lambda item: item['url'] in urls, scards))
        if self.write:
            for scard in scards:
                self.write_card_csv(scard, cat)
        self.close_file()
        return scards
    
    def run_fullcards(self, cat):
        fname = self.get_file(cat)
        file = open(fname, 'r')
        re = csv.DictReader(file, delimiter=self.delim)

        fname_tmp = self.get_tmp_file(cat)
        file_tmp = open(fname_tmp, 'w')
        wr = csv.DictWriter(file_tmp, fieldnames=CARD_KEYS, delimiter=self.delim)
        
        wr.writeheader()
        cnt = 0
        for row in re:
            if row['get_ok'] != 'True' and cnt < self.max_cards:
                row = self.request_card_by_url(row['url'], row)
                cnt = cnt + 1
            wr.writerow(row)
        file.close()
        file_tmp.close()
        os.remove(fname)
        os.rename(fname_tmp, fname)

    def request_scards(self, cat):
        cards = []
        try:
            req = requests.get(URL_ROOT + CAT_URLS[cat], headers=self.headers)
            bs = BeautifulSoup(req.text, 'html.parser')
            wraps = bs.find_all(class_='product-card-wrapper')
        except Exception:
            pass
        time = datetime.datetime.now().ctime()
        for wrap in wraps:
            card = self.init_card()
            card['time'] = time
            try:
                card['url'] = URL_ROOT + wrap.find(class_='product-card__link').get('href')
                card['name'] = wrap.find(class_='product-card__title').text
                card['price'] = wrap.find(class_='product-card__pricing').text
                card['size'] = wrap.find(class_='product-card__size').text
            except Exception:
                pass
            cards.append(card)
        return cards

    def request_card_by_url(self, url, card = None):
        if card == None:
            card = self.init_card()

        card['url'] = url
        card['get_ok'] = False
        card['parse_ok'] = False
        card['time_'] = datetime.datetime.now().ctime()

        try:
            r = requests.get(url)
            card['get_ok'] = True
        except Exception:
            pass  

        try:
            bs = BeautifulSoup(r.text, 'html.parser')
            card['parse_ok'] = True
        except Exception:
            pass
        
        try:
            card['name_'] = bs.find(class_='product__title').text
            card['price_'] = bs.find(class_='product-price-wrapper').find(class_='price-new').text
        except Exception:
            card['parse_ok'] = False
            pass
        
        try: 
            card['brand'] = bs.find(class_='product-brand__title').text
        except Exception:
            pass

        try:
            calories_value = bs.find_all(class_='product-calories-item__value')
            calories_title = bs.find_all(class_='product-calories-item__title')
            for i in range(len(calories_value)):
                card[self.get_calories_key(calories_title[i].text)] = calories_value[i].text
        except Exception:
            pass

        try: 
            card['composition'] = bs.find(class_='product-composition-title').parent.find('p').text
        except Exception:
            pass
        
        if self.verbose:
            print('' if card['get_ok'] and card['parse_ok'] else 'FAILED', url)
        return card

    def write_card_csv(self, card, cat):
        file, isEmpty = self.open_file(cat)
        wr = csv.DictWriter(file, fieldnames=CARD_KEYS, delimiter=self.delim)
        if isEmpty:
            wr.writeheader()
        wr.writerow(card)
    
    def read_urls_csv(self, fname):
        urls = []
        if os.path.isfile(fname):
            file = open(fname, 'r', newline='')
            re = csv.DictReader(file, delimiter=self.delim)
            for row in re:
                urls.append(row['url'].strip())
            file.close()
        return urls

    def open_file(self, cat):
        if self.file == None:
            self.file = open(self.get_file(cat), 'a', newline='')
        return self.file, self.file.tell() == 0
    
    def close_file(self):
        if self.file != None:
            self.file.close()
            self.file = None

    def get_file(self, cat):
        if not os.path.isdir(self.dname):
            os.makedirs(self.dname, mode=0o777)
        return os.path.join(self.dname, cat + self.fext)
    
    def get_tmp_file(self, cat):
        if not os.path.isdir(self.dname):
            os.makedirs(self.dname, mode=0o777)
        return os.path.join(self.dname, cat + '_tmp' + self.fext)

    def get_calories_key(self, calories_title):
        if calories_title.casefold().strip() == 'углеводы':
            return 'carbos'
        if calories_title.casefold().strip() == 'жиры':
            return 'fats'
        if calories_title.casefold().strip() == 'белки':
            return 'proteins'
        if calories_title.casefold().strip() == 'калории':
            return 'calories'
        return None

    def init_card(self):
        card = dict.fromkeys(CARD_KEYS)
        for key in CARD_KEYS:
            card[key] = self.placeholder
        return card


CAT_URLS = {
    'moloko': '/cat/c/114/moloko',
    'syr': '/cat/c/122/syr',
    'tvorog': '/cat/c/117/tvorog',
    'syrki': '/cat/c/656/syrki',
    'jogurty': '/cat/c/119/jogurty',
    'tvorozki': '/cat/c/657/tvorozki',
    'deserty-i-sneki': '/cat/c/658/deserty-i-sneki',
    'ajca': '/cat/c/123/ajca',
    'maslo': '/cat/c/121/maslo',
    'margarin': '/cat/c/659/margarin',
    'spred': '/cat/c/660/spred',
    'kislomolocnye-produkty': '/cat/c/120/kislomolocnye-produkty',
    'smetana': '/cat/c/118/smetana',
    'slivki': '/cat/c/115/slivki',
    'molocnye-konservy': '/cat/c/124/molocnye-konservy',
    'molocnye-koktejli': '/cat/c/116/molocnye-koktejli',
    'ovosi': '/cat/c/150/ovosi',
    'frukty': '/cat/c/153/frukty',
    'agody': '/cat/c/154/agody',
    'zelen-i-salaty': '/cat/c/151/zelen-i-salaty',
    'griby': '/cat/c/155/griby',
    'solena': '/cat/c/149/solena',
    'makarony': '/cat/c/105/makarony',
    'rastitelnoe-maslo': '/cat/c/104/rastitelnoe-maslo',
    'krupy': '/cat/c/107/krupy',
    'bobovye': '/cat/c/745/bobovye',
    'specii-pripravy-i-pranosti': '/cat/c/103/specii-pripravy-i-pranosti',
    'muka': '/cat/c/106/muka',
    'komponenty-dla-vypecki': '/cat/c/102/komponenty-dla-vypecki',
    'sol': '/cat/c/101/sol',
    'cipsy': '/cat/c/202/cipsy',
    'nacos': '/cat/c/774/nacos',
    'sneki': '/cat/c/709/sneki',
    'popkorn': '/cat/c/710/popkorn',
    'suhariki': '/cat/c/711/suhariki',
    'grenki': '/cat/c/712/grenki',
    'kukuruznye-palocki': '/cat/c/713/kukuruznye-palocki',
    'suski-i-baranki': '/cat/c/199/suski-i-baranki',
    'solomki': '/cat/c/714/solomki',
    'hlebnye-palocki': '/cat/c/715/hlebnye-palocki',
    'suhari': '/cat/c/716/suhari',
    'hlebcy': '/cat/c/245/hlebcy',
    'vodorosli': '/cat/c/718/vodorosli',
    'pecene': '/cat/c/197/pecene',
    'vafli': '/cat/c/702/vafli',
    'praniki': '/cat/c/703/praniki',
    'sokolad': '/cat/c/195/sokolad',
    'batonciki': '/cat/c/203/batonciki',
    'sokoladnye-i-orehovye-pasty': '/cat/c/204/sokoladnye-i-orehovye-pasty',
    'konfety': '/cat/c/193/konfety',
    'torty': '/cat/c/201/torty',
    'piroznye': '/cat/c/704/piroznye',
    'pirogi-sdoba-keksy-rulety': '/cat/c/198/pirogi-sdoba-keksy-rulety',
    'zefir': '/cat/c/705/zefir',
    'marmelad': '/cat/c/191/marmelad',
    'pastila': '/cat/c/706/pastila',
    'diabeticeskie-sladosti': '/cat/c/189/diabeticeskie-sladosti',
    'ledency': '/cat/c/194/ledency',
    'draze': '/cat/c/707/draze',
    'vostocnye-sladosti-halva': '/cat/c/188/vostocnye-sladosti-halva',
    'zevatelnaa-rezinka': '/cat/c/190/zevatelnaa-rezinka',
    'morozenoe': '/cat/c/321/morozenoe',
    'voda': '/cat/c/208/voda',
    'gazirovannye-napitki': '/cat/c/209/gazirovannye-napitki',
    'soki': '/cat/c/211/soki',
    'nektary': '/cat/c/737/nektary',
    'kvas': '/cat/c/212/kvas',
    'holodnyj-caj': '/cat/c/210/holodnyj-caj',
    'rastitelnye-napitki': '/cat/c/215/rastitelnye-napitki',
    'bezalkogolnoe-vino': '/cat/c/739/bezalkogolnoe-vino',
    'bezalkogolnoe-pivo': '/cat/c/207/bezalkogolnoe-pivo',
    'sokosoderzasie-napitki': '/cat/c/740/sokosoderzasie-napitki',
    'smuzi': '/cat/c/213/smuzi',
    'energeticeskie-napitki': '/cat/c/206/energeticeskie-napitki',
    'morsy': '/cat/c/214/morsy',
    'kiseli': '/cat/c/742/kiseli',
    'kompoty': '/cat/c/743/kompoty',
    'sbiten-i-uzvary': '/cat/c/744/sbiten-i-uzvary',
    'diabeticeskie-napitki': '/cat/c/216/diabeticeskie-napitki',
    'nasa-pekarna': '/cat/c/196/nasa-pekarna',
    'hleb': '/cat/c/243/hleb',
    'pirogi': '/cat/c/325/pirogi',
    'picca': '/cat/c/1152/picca',
    'lavas-i-lepeski': '/cat/c/244/lavas-i-lepeski',
    'hlebobulocnye-izdelia': '/cat/c/246/hlebobulocnye-izdelia',
    'saslyk': '/cat/c/951/saslyk',
    'maso-pticy': '/cat/c/138/maso-pticy',
    'govadina': '/cat/c/142/govadina',
    'polufabrikaty': '/cat/c/135/polufabrikaty',
    'svinina': '/cat/c/139/svinina',
    'delikatesy-i-kopcenosti': '/cat/c/809/delikatesy-i-kopcenosti',
    'fars': '/cat/c/145/fars',
    'subprodukty': '/cat/c/141/subprodukty',
    'holodcy': '/cat/c/807/holodcy',
    'pastety': '/cat/c/808/pastety',
    'zalivnoe': '/cat/c/810/zalivnoe',
    'kolbasa': '/cat/c/133/kolbasa',
    'vetcina': '/cat/c/783/vetcina',
    'sosiski': '/cat/c/134/sosiski',
    'sardelki': '/cat/c/784/sardelki',
    'spikacki': '/cat/c/785/spikacki',
    'vsa-ryba': '/cat/c/812/vsa-ryba',
    'solenaa-marinovannaa-ryba': '/cat/c/175/solenaa-marinovannaa-ryba',
    'ohlazdennaa-ryba': '/cat/c/176/ohlazdennaa-ryba',
    'zamorozennaa-ryba': '/cat/c/273/zamorozennaa-ryba',
    'kopcenaa-ryba': '/cat/c/177/kopcenaa-ryba',
    'rybnye-konservy-i-kulinaria': '/cat/c/181/rybnye-konservy-i-kulinaria',
    'valenaa-ryba': '/cat/c/794/valenaa-ryba',
    'susenaa-ryba': '/cat/c/178/susenaa-ryba',
    'rybnye-preservy': '/cat/c/184/rybnye-preservy',
    'picca-vareniki-pelmeni-bliny': '/cat/c/58/picca-vareniki-pelmeni-bliny',
    'moreprodukty': '/cat/c/55/moreprodukty',
    'ovosi-i-smesi': '/cat/c/59/ovosi-i-smesi',
    'zamorozennye-polufabrikaty': '/cat/c/56/zamorozennye-polufabrikaty',
    'ryba': '/cat/c/57/ryba',
    'kotlety-naggetsy': '/cat/c/60/kotlety-naggetsy',
    'agody-i-frukty': '/cat/c/61/agody-i-frukty',
    'maso-ptica-i-subprodukty': '/cat/c/63/maso-ptica-i-subprodukty',
    'led': '/cat/c/305/led',
    'ikra': '/cat/c/180/ikra',
    'krabovoe-maso-i-palocki': '/cat/c/182/krabovoe-maso-i-palocki',
    'krevetki': '/cat/c/179/krevetki',
    'midii': '/cat/c/787/midii',
    'kalmary': '/cat/c/786/kalmary',
    'koktejli-iz-moreproduktov': '/cat/c/788/koktejli-iz-moreproduktov',
    'ustricy': '/cat/c/789/ustricy',
    'preservy-iz-moreproduktov': '/cat/c/792/preservy-iz-moreproduktov',
    'sousy': '/cat/c/218/sousy',
    'majonez': '/cat/c/221/majonez',
    'ketcupy-i-tomatnye-sousy': '/cat/c/219/ketcupy-i-tomatnye-sousy',
    'tomatnaa-pasta': '/cat/c/220/tomatnaa-pasta',
    'gorcica': '/cat/c/223/gorcica',
    'hren': '/cat/c/746/hren',
    'uksus': '/cat/c/222/uksus',
    'kofe': '/cat/c/80/kofe',
    'caj': '/cat/c/82/caj',
    'sahar': '/cat/c/83/sahar',
    'kakao': '/cat/c/81/kakao',
    'goracij-sokolad': '/cat/c/766/goracij-sokolad',
    'hlopa': '/cat/c/225/hlopa',
    'musli': '/cat/c/747/musli',
    'podusecki': '/cat/c/748/podusecki',
    'sariki': '/cat/c/749/sariki',
    'kolecki': '/cat/c/750/kolecki',
    'granola': '/cat/c/752/granola',
    'ris': '/cat/c/754/ris',
    'kasi': '/cat/c/756/kasi',
    'kasi-bystrogo-prigotovlenia': '/cat/c/755/kasi-bystrogo-prigotovlenia',
    'lapsa': '/cat/c/170/lapsa',
    'supy': '/cat/c/169/supy',
    'pure': '/cat/c/171/pure',
    'vtorye-bluda': '/cat/c/173/vtorye-bluda',
    'ovosnye-konservy': '/cat/c/76/ovosnye-konservy',
    'rybnye-konservy': '/cat/c/75/rybnye-konservy',
    'masnye-konservy': '/cat/c/78/masnye-konservy',
    'fruktovye-konservy': '/cat/c/77/fruktovye-konservy',
    'orehi': '/cat/c/159/orehi',
    'semecki': '/cat/c/161/semecki',
    'smesi-orehov-i-suhofruktov': '/cat/c/158/smesi-orehov-i-suhofruktov',
    'suhofrukty': '/cat/c/160/suhofrukty',
    'med': '/cat/c/112/med',
    'varene': '/cat/c/111/varene',
    'dzem': '/cat/c/109/dzem',
    'konfitur': '/cat/c/775/konfitur',
    'siropy': '/cat/c/110/siropy',
    'vino': '/cat/c/2/vino',
    'igristye-vina': '/cat/c/3/igristye-vina',
    'sampanskoe': '/cat/c/758/sampanskoe',
    'viski-burbon': '/cat/c/5/viski-burbon',
    'konak': '/cat/c/4/konak',
    'rom': '/cat/c/15/rom',
    'vodka-absent': '/cat/c/6/vodka-absent',
    'samogon': '/cat/c/761/samogon',
    'pivo': '/cat/c/9/pivo',
    'sidr': '/cat/c/7/sidr',
    'medovuha': '/cat/c/762/medovuha',
    'tekila': '/cat/c/13/tekila',
    'nastojki': '/cat/c/8/nastojki',
    'dzin': '/cat/c/10/dzin',
    'brendi': '/cat/c/14/brendi',
    'likery': '/cat/c/16/likery',
    'vermut': '/cat/c/764/vermut',
    'balzam': '/cat/c/17/balzam',
    'slaboalkogolnye-napitki': '/cat/c/11/slaboalkogolnye-napitki'
}

CAT_NAMES = {
    'moloko': 'Молоко',
    'syr': 'Сыр',
    'tvorog': 'Творог',
    'syrki': 'Сырки',
    'jogurty': 'Йогурты',
    'tvorozki': 'Творожки',
    'deserty-i-sneki': 'Десерты и снеки',
    'ajca': 'Яйца',
    'maslo': 'Масло',
    'margarin': 'Маргарин',
    'spred': 'Спред',
    'kislomolocnye-produkty': 'Кисломолочные продукты',
    'smetana': 'Сметана',
    'slivki': 'Сливки',
    'molocnye-konservy': 'Молочные консервы',
    'molocnye-koktejli': 'Молочные коктейли',
    'ovosi': 'Овощи',
    'frukty': 'Фрукты',
    'agody': 'Ягоды',
    'zelen-i-salaty': 'Зелень и салаты',
    'griby': 'Грибы',
    'solena': 'Соленья',
    'makarony': 'Макароны',
    'rastitelnoe-maslo': 'Растительное масло',
    'krupy': 'Крупы',
    'bobovye': 'Бобовые',
    'specii-pripravy-i-pranosti': 'Специи, приправы и пряности',
    'muka': 'Мука',
    'komponenty-dla-vypecki': 'Компоненты для выпечки',
    'sol': 'Соль',
    'cipsy': 'Чипсы',
    'nacos': 'Начос',
    'sneki': 'Снеки',
    'popkorn': 'Попкорн',
    'suhariki': 'Сухарики',
    'grenki': 'Гренки',
    'kukuruznye-palocki': 'Кукурузные палочки',
    'suski-i-baranki': 'Сушки и баранки',
    'solomki': 'Соломки',
    'hlebnye-palocki': 'Хлебные палочки',
    'suhari': 'Сухари',
    'hlebcy': 'Хлебцы',
    'vodorosli': 'Водоросли',
    'pecene': 'Печенье',
    'vafli': 'Вафли',
    'praniki': 'Пряники',
    'sokolad': 'Шоколад',
    'batonciki': 'Батончики',
    'sokoladnye-i-orehovye-pasty': 'Шоколадные и ореховые пасты',
    'konfety': 'Конфеты',
    'torty': 'Торты',
    'piroznye': 'Пирожные',
    'pirogi-sdoba-keksy-rulety': 'Пироги, сдоба, кексы, рулеты',
    'zefir': 'Зефир',
    'marmelad': 'Мармелад',
    'pastila': 'Пастила',
    'diabeticeskie-sladosti': 'Диабетические сладости',
    'ledency': 'Леденцы',
    'draze': 'Драже',
    'vostocnye-sladosti-halva': 'Восточные сладости, халва',
    'zevatelnaa-rezinka': 'Жевательная резинка',
    'morozenoe': 'Мороженое',
    'voda': 'Вода',
    'gazirovannye-napitki': 'Газированные напитки',
    'soki': 'Соки',
    'nektary': 'Нектары',
    'kvas': 'Квас',
    'rastitelnye-napitki': 'Растительные напитки',
    'holodnyj-caj': 'Холодный чай',
    'bezalkogolnoe-pivo': 'Безалкогольное пиво',
    'bezalkogolnoe-vino': 'Безалкогольное вино',
    'sokosoderzasie-napitki': 'Сокосодержащие напитки',
    'smuzi': 'Смузи',
    'energeticeskie-napitki': 'Энергетические напитки',
    'morsy': 'Морсы',
    'kiseli': 'Кисели',
    'kompoty': 'Компоты',
    'sbiten-i-uzvary': 'Сбитень и узвары',
    'diabeticeskie-napitki': 'Диабетические напитки',
    'nasa-pekarna': 'Наша пекарня',
    'hleb': 'Хлеб',
    'pirogi': 'Пироги',
    'picca': 'Пицца',
    'lavas-i-lepeski': 'Лаваш и лепёшки',
    'hlebobulocnye-izdelia': 'Хлебобулочные изделия',
    'saslyk': 'Шашлык',
    'maso-pticy': 'Мясо птицы',
    'govadina': 'Говядина',
    'polufabrikaty': 'Полуфабрикаты',
    'svinina': 'Свинина',
    'delikatesy-i-kopcenosti': 'Деликатесы и копчёности',
    'fars': 'Фарш',
    'subprodukty': 'Субпродукты',
    'holodcy': 'Холодцы',
    'pastety': 'Паштеты',
    'zalivnoe': 'Заливное',
    'kolbasa': 'Колбаса',
    'vetcina': 'Ветчина',
    'sosiski': 'Сосиски',
    'sardelki': 'Сардельки',
    'spikacki': 'Шпикачки',
    'vsa-ryba': 'Вся рыба',
    'solenaa-marinovannaa-ryba': 'Солёная, маринованная рыба',
    'ohlazdennaa-ryba': 'Охлаждённая рыба',
    'zamorozennaa-ryba': 'Замороженная рыба',
    'kopcenaa-ryba': 'Копчёная рыба',
    'rybnye-konservy-i-kulinaria': 'Рыбные консервы и кулинария',
    'valenaa-ryba': 'Вяленая рыба',
    'susenaa-ryba': 'Сушёная рыба',
    'rybnye-preservy': 'Рыбные пресервы',
    'picca-vareniki-pelmeni-bliny': 'Пицца, вареники, пельмени, блины',
    'moreprodukty': 'Морепродукты',
    'ovosi-i-smesi': 'Овощи и смеси',
    'zamorozennye-polufabrikaty': 'Замороженные полуфабрикаты',
    'ryba': 'Рыба',
    'kotlety-naggetsy': 'Котлеты, наггетсы',
    'agody-i-frukty': 'Ягоды и фрукты',
    'maso-ptica-i-subprodukty': 'Мясо, птица и субпродукты',
    'led': 'Лёд',
    'ikra': 'Икра',
    'krabovoe-maso-i-palocki': 'Крабовое мясо и палочки',
    'krevetki': 'Креветки',
    'midii': 'Мидии',
    'kalmary': 'Кальмары',
    'koktejli-iz-moreproduktov': 'Коктейли из морепродуктов',
    'ustricy': 'Устрицы',
    'preservy-iz-moreproduktov': 'Пресервы из морепродуктов',
    'sousy': 'Соусы',
    'majonez': 'Майонез',
    'ketcupy-i-tomatnye-sousy': 'Кетчупы и томатные соусы',
    'tomatnaa-pasta': 'Томатная паста',
    'gorcica': 'Горчица',
    'hren': 'Хрен',
    'uksus': 'Уксус',
    'kofe': 'Кофе',
    'caj': 'Чай',
    'sahar': 'Сахар',
    'kakao': 'Какао',
    'goracij-sokolad': 'Горячий шоколад',
    'hlopa': 'Хлопья',
    'musli': 'Мюсли',
    'podusecki': 'Подушечки',
    'sariki': 'Шарики',
    'kolecki': 'Колечки',
    'granola': 'Гранола',
    'ris': 'Рис',
    'kasi': 'Каши',
    'kasi-bystrogo-prigotovlenia': 'Каши быстрого приготовления',
    'lapsa': 'Лапша',
    'supy': 'Супы',
    'pure': 'Пюре',
    'vtorye-bluda': 'Вторые блюда',
    'ovosnye-konservy': 'Овощные консервы',
    'rybnye-konservy': 'Рыбные консервы',
    'masnye-konservy': 'Мясные консервы',
    'fruktovye-konservy': 'Фруктовые консервы',
    'orehi': 'Орехи',
    'semecki': 'Семечки',
    'smesi-orehov-i-suhofruktov': 'Смеси орехов и сухофруктов',
    'suhofrukty': 'Сухофрукты',
    'med': 'Мёд',
    'varene': 'Варенье',
    'dzem': 'Джем',
    'konfitur': 'Конфитюр',
    'siropy': 'Сиропы',
    'vino': 'Вино',
    'igristye-vina': 'Игристые вина',
    'sampanskoe': 'Шампанское',
    'viski-burbon': 'Виски, бурбон',
    'konak': 'Коньяк',
    'rom': 'Ром',
    'vodka-absent': 'Водка, Абсент',
    'samogon': 'Самогон',
    'pivo': 'Пиво',
    'sidr': 'Сидр',
    'medovuha': 'Медовуха',
    'tekila': 'Текила',
    'nastojki': 'Настойки',
    'dzin': 'Джин',
    'brendi': 'Бренди',
    'likery': 'Ликёры',
    'vermut': 'Вермут',
    'balzam': 'Бальзам',
    'slaboalkogolnye-napitki': 'Слабоалкогольные напитки'
 }