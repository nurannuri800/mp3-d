from flask import Flask, request, render_template, Response
import yt_dlp
import re
import unicodedata
import browser_cookie3  # Çerezleri otomatik almak için

app = Flask(__name__)

@app.route('/')
def index():
    # Ana arama ve indirme sayfasını gösterir
    return render_template('index.html')

@app.route('/process', methods=['GET'])
def process():
    query = request.args.get('query')
    if not query:
        return "No input provided", 400

    # Kullanıcının bir YouTube linki mi yoksa arama sorgusu mu girdiğini kontrol et
    if "youtube.com" in query or "youtu.be" in query:
        # Kullanıcı bir link yapıştırdıysa, doğrudan indirme sayfasına yönlendir
        return download_video(query)
    else:
        # Kullanıcı bir anahtar kelime girdi; arama sonuçlarını döndür
        return search_videos(query)

def get_browser_cookies():
    """Tarayıcıdan çerezleri otomatik olarak al."""
    try:
        cookies = browser_cookie3.firefox(domain_name="youtube.com")
        # Eğer Chrome kullanıyorsanız: browser_cookie3.chrome(domain_name="youtube.com")
        return cookies
    except Exception as e:
        raise RuntimeError(f"Çerezler alınırken hata oluştu: {e}")

def search_videos(query):
    try:
        # YouTube'da arama yap
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,  # Video detaylarını indirmeden listele
        }

        # Çerezleri otomatik olarak ekle
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.cookiejar = get_browser_cookies()
            search_results = ydl.extract_info(f"ytsearch10:{query}", download=False)

        # Sonuçları işleme
        videos = [
            {
                'id': entry['id'],
                'title': entry['title'],
                'url': f"https://www.youtube.com/watch?v={entry['id']}"
            }
            for entry in search_results.get('entries', [])
        ]

        return render_template('search_results.html', videos=videos)

    except Exception as e:
        return f"Error: {str(e)}", 500

def download_video(video_url):
    try:
        # MP3 için yt-dlp ayarları
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        # Çerezleri otomatik olarak ekle
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.cookiejar = get_browser_cookies()
            result = ydl.extract_info(video_url, download=False)
            video_title = result.get('title', 'audio')

        # Güvenli dosya adı oluştur
        sanitized_title = re.sub(r'[^\w\s-]', '', unicodedata.normalize('NFKD', video_title)).strip().replace(' ', '_')

        def stream_file():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.cookiejar = get_browser_cookies()
                with ydl.urlopen(result['url']) as stream:
                    for chunk in iter(lambda: stream.read(64 * 1024), b""):
                        yield chunk

        return Response(
            stream_file(),
            content_type='audio/mpeg',
            headers={
                'Content-Disposition': f'attachment; filename="{sanitized_title}.mp3"',
                'Cache-Control': 'no-cache',
                'Transfer-Encoding': 'chunked',
            },
        )

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5000', debug=True, threaded=True)
