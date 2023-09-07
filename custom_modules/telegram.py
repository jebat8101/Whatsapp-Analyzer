import streamlit as st
import numpy as np
import pandas as pd
import altair as alt
import nltk
import requests
import io
import json

from datetime import datetime
from random import randint
from wordcloud import WordCloud
from streamlit_extras.badges import badge
from PIL import Image
from nltk.sentiment import SentimentIntensityAnalyzer
from nlp import sentiment_analysis


def main():
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html = True)

    # Create title and header
    col1, col2, col3 = st.columns([0.047, 0.265, 0.035])
    
    with col1:
        url = 'https://github.com/tsu2000/tele_dashboard/raw/main/images/telegram.png'
        response = requests.get(url)
        img = Image.open(io.BytesIO(response.content))
        st.image(img, output_format = 'png')

    with col2:
        st.title('&nbsp; Telegram Chat Dashboard')

    with col3:
        badge(type = 'github', name = 'tsu2000/tele_dashboard', url = 
'https://github.com/tsu2000/tele_dashboard')

    st.markdown('---')

    # Create sidebar to read files
    with st.sidebar:
        st.title('📤 &nbsp; User Inputs')

        if 'key' not in st.session_state: 
            st.session_state.key = str(randint(1000, 100000000))

        with st.expander("View sample Telegram chat file:"):

            # Create downloadable JSON format
            @st.cache_data
            def initial_json(url):
                data = requests.get(url).json()
                return json.dumps(data)

            st.download_button(
                label = 'Download sample JSON',
                file_name = 'sample_tele_chat_data.json',
                mime = 'application/json',
                help = 'Download sample Telegram JSON file',
                data = 
initial_json('https://raw.githubusercontent.com/tsu2000/tele_dashboard/main/sample.json')
            )

        uploaded_files = st.file_uploader('Upload all Telegram chat messages to be processed 
here (in `.json` format) - View 
[**instructions**](https://github.com/tsu2000/tele_dashboard/blob/main/instructions.md)', 
                                           accept_multiple_files = True,
                                           key = st.session_state.key,
                                           type = '.json')

        if uploaded_files != []:
            st.markdown('---')
            clear_btn = st.button('Clear All')
            
            if clear_btn and 'key' in st.session_state.keys():
                st.session_state.pop('key')
                st.experimental_rerun()

    # Main page start
    if not uploaded_files:
        st.error('No files have been uploaded. Please upload at least 1 exported Telegram chat 
file (in `.json` format). If you have multiple `.json` files, upload them in chronological 
order. Try not to upload files which are too large (>200MB total), as they ~~may~~ **will** 
crash the app. You have been warned!', icon = '🚨')
    else:
        raw_data_files = []

        for uploaded_file in uploaded_files:
            bytes_data = uploaded_file.read()
            raw_data_files.append(bytes_data)

        @st.cache_data
        def days_between(d1, d2):
            d1 = datetime.strptime(d1, "%Y-%m-%d")
            d2 = datetime.strptime(d2, "%Y-%m-%d")
            return abs((d2 - d1).days)

        # Data processing
        days = days_between(json.loads(raw_data_files[0])['messages'][0]['date'][:10], 
datetime.now().strftime('%Y-%m-%d'))

        # Determing length of JSON object
        init_data = json.loads(raw_data_files[0])

        if len(raw_data_files) > 1:
            for rdf in raw_data_files[1:]:
                more_data = json.loads(rdf)
                init_data['messages'].extend(more_data['messages'])

        all_data = init_data

        # Obtaining statistics about the data
        message_sent = [x['from'] for x in all_data['messages'] if 'from' in x]
        users = list(set(message_sent))

        user_and_message_and_date = [[x['from'], ''.join([y['text'] for y in 
x['text_entities']]), x['date'][:10]] for x in all_data['messages'] if ('from' in x and 
'text_entities' in x and 'date' in x)]
        
        # MAIN DATAFRAME
        df = pd.DataFrame(data = user_and_message_and_date, columns = ['User', 'Message', 
'Date'])

        # Dataframe for bar chart
        msg_counts = df['User'].value_counts()
        d2 = {'User': msg_counts.index, 'Total Message Count': msg_counts.values}
        df2 = pd.DataFrame(data = d2)

        alt_bar_chart = alt.Chart(df2).mark_bar().encode(
            x = alt.X('Total Message Count:Q'),
            y = alt.Y('User:N', sort = alt.EncodingSortField(field = "User", op = "count", order 
= 'ascending')),
            color = alt.Color('User', sort = '-x')
        )

        # Dataframe for line chart
        dates = df['Date'].value_counts()
        d3 = {'Date': dates.index, 'Daily Messages Sent': dates.values}
        df3 = pd.DataFrame(data = d3)
        df3['Date'] = pd.to_datetime(df3['Date'])

        alt_line_chart = alt.Chart(df3).mark_line(
            point = alt.OverlayMarkDef(color = 'green', shape = 'diamond')
        ).encode(
            x = 'Date:T',
            y = 'Daily Messages Sent',
            color = alt.value('green'),
        ).interactive()

        # Dataframe for scatter plot
        df['Message word count'] = [len(msg.split()) for msg in df['Message']]
        df4 = df[df['Message word count'] != 0]
        avg_word_count = df4.groupby('User')['Message word count'].mean()
        
        df_scatter = pd.concat([avg_word_count, msg_counts], axis = 1).reset_index()
        df4 = df_scatter.rename(columns = {'index': 'User', 'Message word count': 'Average word 
count', 'User': 'Total messages sent'})

        alt_scatter_plot = alt.Chart(df4).mark_circle(size = 75, opacity = 0.75).encode(
            x = alt.X('Average word count', title = 'Average word count per message'),
            y = 'Total messages sent',
            color = 'User',
            tooltip = ['User', 'Average word count', 'Total messages sent']
        ).interactive()


        # # # # # # APP VISUALISATION START # # # # # #

        # Chat Metrics
        st.markdown(f"### Chat Overview - {all_data['name']}")
        col1, col2, col3 = st.columns(3)
        col1.metric('No. of Chat Users 👥', f'{len(set(users)):,}')
        col2.metric('No. of Messages &nbsp; 💬', f'{len(message_sent):,}')
        col3.metric("Chat Group Age &nbsp; 🗓️", f'{days:,} d')

        # Bar chart
        st.markdown('### Active users')
        st.altair_chart(alt_bar_chart, use_container_width = True)

        # Line chart
        st.markdown('### Daily no. of messages sent')
        st.altair_chart(alt_line_chart, use_container_width = True)

        # Scatter plot
        st.markdown('#### Average no. of words per message VS Total no. of messages sent')
        st.altair_chart(alt_scatter_plot, use_container_width = True)

        # Word cloud
        st.markdown('### Word Cloud')
        all_words = ' '.join(df['Message'])
        custom_stopwords = set([
        "ada", "inikah", "sampai", "adakah", "inilah", "sana", "adakan", "itu", "sangat", 
"adalah",
        "itukah", "sangatlah", "adanya", "itulah", "saya", "adapun", "jadi", "se", "agak", 
"jangan",
        "seandainya", "agar", "janganlah", "sebab", "akan", "jika", "sebagai", "aku", "jikalau",
        "sebagaimana", "akulah", "jua", "sebanyak", "akupun", "juapun", "sebelum", "al", "juga",
        "sebelummu", "alangkah", "kalau", "sebelumnya", "allah", "kami", "sebenarnya", "amat",
        "kamikah", "secara", "antara", "kamipun", "sedang", "antaramu", "kamu", "sedangkan", 
"antaranya",
        "kamukah", "sedikit", "apa", "kamupun", "sedikitpun", "apa-apa", "katakan", "segala", 
"apabila",
        "ke", "sehingga", "apakah", "kecuali", "sejak", "apapun", "kelak", "sekalian", "atas", 
"kembali",
        "sekalipun", "atasmu", "kemudian", "sekarang", "atasnya", "kepada", "sekitar", "atau", 
"kepadaku",
        "selain", "ataukah", "kepadakulah", "selalu", "ataupun", "kepadamu", "selama", 
"bagaimana",
        "kepadanya", "selama-lamanya", "bagaimanakah", "kepadanyalah", "seluruh", "bagimu", 
"kerana",
        "seluruhnya", "baginya", "kesan", "semua", "bahawa", "ketika", "semuanya", 
"bahawasanya",
        "kini", "semula", "bahkan", "kita", "senantiasa", "bahwa", "ku", "sendiri", "banyak",
        "kurang", "sentiasa", "banyaknya", "lagi", "seolah", "barangsiapa", "lain", 
"seolah-olah",
        "bawah", "lalu", "seorangpun", "beberapa", "lamanya", "separuh", "begitu", "langsung", 
"sepatutnya",
        "begitupun", "lebih", "seperti", "belaka", "maha", "seraya", "belum", "mahu", "sering",
        "belumkah", "mahukah", "serta", "berada", "mahupun", "seseorang", "berapa", "maka", 
"sesiapa",
        "berikan", "malah", "sesuatu", "beriman", "mana", "sesudah", "berkenaan", "manakah", 
"sesudahnya",
        "berupa", "manapun", "sesungguhnya", "beserta", "masih", "sesungguhnyakah", "biarpun",
        "masing", "setelah", "bila", "masing-masing", "setiap", "bilakah", "melainkan", "siapa",
        "bilamana", "memang", "siapakah", "bisa", "mempunyai", "sini", "boleh", "mendapat", 
"situ",
        "bukan", "mendapati", "situlah", "bukankah", "mendapatkan", "suatu", "bukanlah", 
"mengadakan",
        "sudah", "dahulu", "mengapa", "sudahkah", "dalam", "mengapakah", "sungguh", "dalamnya",
        "mengenai", "sungguhpun", "dan", "menjadi", "supaya", "dapat", "menyebabkan", "tadinya", 
"dapati",
        "menyebabkannya", "tahukah", "dapatkah", "mereka", "tak", "dapatlah", "merekalah", 
"tanpa",
        "dari", "merekapun", "tanya", "daripada", "meskipun", "tanyakanlah", "daripadaku", "mu",
        "tapi", "daripadamu", "nescaya", "telah", "daripadanya", "niscaya", "tentang", "demi", 
"nya",
        "tentu", "demikian", "olah", "terdapat", "demikianlah", "oleh", "terhadap", "dengan", 
"orang",
        "terhadapmu", "dengannya", "pada", "termasuk", "di", "padahal", "terpaksa", "dia", 
"padamu",
        "tertentu", "dialah", "padanya", "tetapi", "didapat", "paling", "tiada", "didapati", 
"para",
        "tiadakah", "dimanakah", "pasti", "tiadalah", "engkau", "patut", "tiap", "engkaukah", 
"patutkah",
        "tiap-tiap", "engkaulah", "per", "tidak", "engkaupun", "pergilah", "tidakkah", "hai", 
"perkara",
        "tidaklah", "hampir", "perkaranya", "turut", "hampir-hampir", "perlu", "untuk", "hanya", 
"pernah",
        "untukmu", "hanyalah", "pertama", "wahai", "hendak", "pula", "walau", "hendaklah", 
"pun",
        "walaupun", "hingga", "sahaja", "ya", "ia", "saja", "yaini", "iaitu", "saling", "yaitu",
        "ialah", "pa", "nak", "sama", "yakni", "ianya", "sama-sama", "yang", "inginkah", 
"samakah", "sambil", "yg", "itu", "ini", "tu", "ni", 
"abdul","abdullah","acara","ada","adalah","ahmad","air","akan","akhbar","akhir","aktiviti","alam","amat","amerika","anak","anggota","antara","antarabangsa","apa","apabila","april","as","asas","asean","asia","asing","atas","atau","australia","awal","awam","bagaimanapun","bagi","bahagian","bahan","baharu","bahawa","baik","bandar","bank","banyak","barangan","baru","baru-baru","bawah","beberapa","bekas","beliau","belum","berada","berakhir","berbanding","berdasarkan","berharap","berikutan","berjaya","berjumlah","berkaitan","berkata","berkenaan","berlaku","bermula","bernama","bernilai","bersama","berubah","besar","bhd","bidang","bilion","bn","boleh","bukan","bulan","bursa","cadangan","china","dagangan","dalam","dan","dana","dapat","dari","daripada","dasar","datang","datuk","demikian","dengan","depan","derivatives","dewan","di","diadakan","dibuka","dicatatkan","dijangka","diniagakan","dis","disember","ditutup","dolar","dr","dua","dunia","ekonomi","eksekutif","eksport","empat","enam","faedah","feb","global","hadapan","hanya","harga","hari","hasil","hingga","hubungan","ia","iaitu","ialah","indeks","india","indonesia","industri","ini","islam","isnin","isu","itu","jabatan","jalan","jan","jawatan","jawatankuasa","jepun","jika","jualan","juga","julai","jumaat","jumlah","jun","juta","kadar","kalangan","kali","kami","kata","katanya","kaunter","kawasan","ke","keadaan","kecil","kedua","kedua-dua","kedudukan","kekal","kementerian","kemudahan","kenaikan","kenyataan","kepada","kepentingan","keputusan","kerajaan","kerana","kereta","kerja","kerjasama","kes","keselamatan","keseluruhan","kesihatan","ketika","ketua","keuntungan","kewangan","khamis","kini","kira-kira","kita","klci","klibor","komposit","kontrak","kos","kuala","kuasa","kukuh","kumpulan","lagi","lain","langkah","laporan","lebih","lepas","lima","lot","luar","lumpur","mac","mahkamah","mahu","majlis","makanan","maklumat","malam","malaysia","mana","manakala","masa","masalah","masih","masing-masing","masyarakat","mata","media","mei","melalui","melihat","memandangkan","memastikan","membantu","membawa","memberi","memberikan","membolehkan","membuat","mempunyai","menambah","menarik","menawarkan","mencapai","mencatatkan","mendapat","mendapatkan","menerima","menerusi","mengadakan","mengambil","mengenai","menggalakkan","menggunakan","mengikut","mengumumkan","mengurangkan","meningkat","meningkatkan","menjadi","menjelang","menokok","menteri","menunjukkan","menurut","menyaksikan","menyediakan","mereka","merosot","merupakan","mesyuarat","minat","minggu","minyak","modal","mohd","mudah","mungkin","naik","najib","nasional","negara","negara-negara","negeri","niaga","nilai","nov","ogos","okt","oleh","operasi","orang","pada","pagi","paling","pameran","papan","para","paras","parlimen","parti","pasaran","pasukan","pegawai","pejabat","pekerja","pelabur","pelaburan","pelancongan","pelanggan","pelbagai","peluang","pembangunan","pemberita","pembinaan","pemimpin","pendapatan","pendidikan","penduduk","penerbangan","pengarah","pengeluaran","pengerusi","pengguna","pengurusan","peniaga","peningkatan","penting","peratus","perdagangan","perdana","peringkat","perjanjian","perkara","perkhidmatan","perladangan","perlu","permintaan","perniagaan","persekutuan","persidangan","pertama","pertubuhan","pertumbuhan","perusahaan","peserta","petang","pihak","pilihan","pinjaman","polis","politik","presiden","prestasi","produk","program","projek","proses","proton","pukul","pula","pusat","rabu","rakan","rakyat","ramai","rantau","raya","rendah","ringgit","rumah","sabah","sahaja","saham","sama","sarawak","satu","sawit","saya","sdn","sebagai","sebahagian","sebanyak","sebarang","sebelum","sebelumnya","sebuah","secara","sedang","segi","sehingga","sejak","sekarang","sektor","sekuriti","selain","selama","selasa","selatan","selepas","seluruh","semakin","semalam","semasa","sementara","semua","semula","sen","sendiri","seorang","sepanjang","seperti","sept","september","serantau","seri","serta","sesi","setiap","setiausaha","sidang","singapura","sini","sistem","sokongan","sri","sudah","sukan","suku","sumber","supaya","susut","syarikat","syed","tahap","tahun","tan","tanah","tanpa","tawaran","teknologi","telah","tempat","tempatan","tempoh","tenaga","tengah","tentang","terbaik","terbang","terbesar","terbuka","terdapat","terhadap","termasuk","tersebut","terus","tetapi","thailand","tiada","tidak","tiga","timbalan","timur","tindakan","tinggi","tun","tunai","turun","turut","unit","untuk","untung","urus","usaha","utama","walaupun","wang","wanita","wilayah","yang"
        ,"this", "message", "omitted", "rm", "a", "5", "in", "of", "4","2018","and", "foto", 
"la", "dah", "nk", "kena", "ini.", "2", "3", "2021", "to", "1", "muhammad", "buat", "the", 
"off"])


        wc = WordCloud(mode = "RGBA", stopwords=custom_stopwords, max_words = 100, 
background_color = None, width = 2000, height = 1000, margin = 2)
        wc_fig = wc.generate(all_words)
        
        st.image(wc_fig.to_array(), use_column_width = True)

        # Sentiment Analysis (Experimental)
        st.markdown('### Sentiment Analysis')
        st.markdown('**Disclaimer**: Sentiment analysis is limited to purely text messages in 
the chat group, with no support for stickers/emojis/other files.')

        vader = SentimentIntensityAnalyzer()

        all_msg_df = df[df['Message'] != '']
        all_msg_df['Sentiment'] = all_msg_df['Message'].apply(lambda x: 
vader.polarity_scores(x)['compound'])
        all_msg_df['Sentiment Type'] = all_msg_df['Sentiment'].apply(lambda x: 'Positive' if x > 
0 else 'Negative' if x < 0 else 'Neutral')

        summary_df = all_msg_df.groupby(['Sentiment Type']).agg({'Sentiment': 'sum', 'Sentiment 
Type': 'count'})

        # st.dataframe(summary_df, use_container_width = True)

        series = sentiment_analysis(summary_df)

        source = pd.DataFrame(index = series.index, data = series.values, columns = 
['Percentage']).reset_index(names = 'Sentiment Type')

        chart = alt.Chart(source).mark_bar().encode(
            x = alt.X('Percentage', axis=alt.Axis(format='%')),
            y = 'Sentiment Type',
            color = alt.Color('Sentiment Type', scale = alt.Scale(range = ['#48C416', '#CEA200', 
'#DF2727']), legend = None)
        )

        text = chart.mark_text(align = 'left', dx = 5).encode(
            text = alt.Text('Percentage:Q', format = ',.2%'),
        )

        sentiment_final = (chart + text).properties(
            title = 'Percentage of each type of sentiment in chat group',
            width = 800,
            height = 300
        ).configure_title(
            fontSize = 15,
            offset = 15,
            anchor = 'middle'
        ).configure_axisX(
            titlePadding = 20
        ).configure_axisY(
            titlePadding = 20
        )

        st.altair_chart(sentiment_final, use_container_width = True)

        st.markdown('---')


if __name__ == "__main__":
    nltk.download('vader_lexicon')
    st.set_page_config(page_title = 'Telegram Dashboard', page_icon = '📈')
    main()
