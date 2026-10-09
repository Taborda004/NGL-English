from bs4 import BeautifulSoup
import base64

class ContentExtractor:
    def __init__(self, page):
        self.page = page
        
    def extract_context(self):
        """Extract all visible text from the main exercise area and all iframes."""
        if not self.page:
            return ""
        try:
            frames_to_check = [self.page.main_frame] + getattr(self.page, 'frames', [])
            
            # 1. Prioridad: En actividades y exámenes multi-pantalla de Avallain / NGL,
            # extraer ÚNICAMENTE el texto de la pantalla activa visible para no abrumar a la IA
            for frame in frames_to_check:
                try:
                    active_text = frame.evaluate(r"""() => {
                        const $ = window.jQuery;
                        if (!$) return null;
                        
                        let activeWrap = $('.content-wrap:visible, .activity:visible').first();
                        if (activeWrap.length === 0) {
                            activeWrap = $('.content-wrap, .activity').filter(function() { return $(this).css('display') !== 'none'; }).first();
                        }
                        
                        if (activeWrap.length > 0 || wraps.length > 0) {
                            const title = $('.learningObject__title, .lo-title, h1, h2').first().text().trim();
                            const target = activeWrap.length > 0 ? activeWrap : $('.activity:visible').first();
                            let content = target.length > 0 ? target.text().trim() : '';
                            
                            // Si es un ejercicio de matching/linking lines, estructurar los elementos izquierdo y derecho
                            const handles = target.find('.isLinkingMultipleLines__handle, .linkingLines__item .handle, .handle');
                            if (handles.length > 0) {
                                const lItems = [];
                                const rItems = [];
                                handles.each(function() {
                                    const h = $(this);
                                    const isLeft = h.hasClass('right_handle') || h.closest('.linkingLines__item--left, .left').length > 0;
                                    const container = h.closest('.element, [class*="item"], .isLinkingMultipleLines__item');
                                    const txt = container.find('[id*="content"], .text').text().trim();
                                    if (isLeft) {
                                        lItems.push(txt || ('Audio ' + (lItems.length + 1)));
                                    } else {
                                        rItems.push(txt);
                                    }
                                });
                                if (lItems.length > 0 && rItems.length > 0) {
                                    let matchSection = '\n\n--- MATCHING ITEMS TO PAIR ---';
                                    lItems.forEach((it, i) => { matchSection += `\nLeft ${i + 1}: ${it}`; });
                                    rItems.forEach((it, i) => { matchSection += `\nRight ${i + 1}: ${it}`; });
                                    content += matchSection;
                                }
                            }
                            
                            const segs = Array.from(document.querySelectorAll('.transcript-segment, .player__transcript-body p'))
                                .map(p => p.textContent.replace(/\s+/g, ' ').trim()).filter(Boolean);
                            const transcript = segs.length > 0 ? ("\n\n--- VIDEO / AUDIO TRANSCRIPT ---\n" + segs.join(' ')) : '';
                            
                            let res = '';
                            if (title) res += title + '\n\n';
                            res += content + transcript;
                            return res.trim();
                        }
                        return null;
                    }""")
                    if active_text and len(active_text) > 20:
                        return active_text
                except Exception:
                    pass

            # 2. Fallback estándar para páginas o iframes genéricos
            texts = []
            seen_html = set()
            
            for frame in frames_to_check:
                try:
                    html = frame.content()
                    if html in seen_html:
                        continue
                    seen_html.add(html)
                    
                    soup = BeautifulSoup(html, 'html.parser')
                    for script in soup(["script", "style"]):
                        script.extract()
                    
                    text = soup.get_text(separator='\n', strip=True)
                    if len(text) > 30:
                        texts.append(text)
                except:
                    pass
            # Extraer transcripciones integradas en los reproductores de video/audio
            transcripts = []
            for frame in frames_to_check:
                try:
                    t_text = frame.evaluate(r"""() => {
                        const segs = Array.from(document.querySelectorAll('.transcript-segment, .player__transcript-body p')).map(p => p.textContent.replace(/\s+/g, ' ').trim()).filter(Boolean);
                        return segs.join(' ');
                    }""")
                    if t_text and len(t_text) > 20:
                        transcripts.append(t_text)
                except:
                    pass
            
            if transcripts:
                texts.append("\n\n--- VIDEO / AUDIO TRANSCRIPT ---\n" + "\n".join(transcripts))
                    
            return "\n\n".join(texts)
        except Exception as e:
            return str(e)

    def extract_screenshot_b64(self):
        """Returns base64 encoded compressed JPEG screenshot for instant upload."""
        if not self.page:
            return None
        try:
            # full_page=True captura toda la altura de la página (evita que las preguntas de abajo se corten por scroll)
            image_bytes = self.page.screenshot(type="jpeg", quality=90, full_page=True)
            return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            print(f"Screenshot error: {e}")
            return None

    def extract_audios_b64(self, context):
        """Extracts and downloads audio files only for the currently active exercise screen."""
        if not self.page or not context:
            return []
            
        frames_to_check = [self.page.main_frame] + getattr(self.page, 'frames', [])
        
        # 1. Si ya existe transcripción de texto visible en el reproductor de la pantalla activa,
        # no gastamos tiempo ni ancho de banda descargando el archivo de audio.
        for frame in frames_to_check:
            try:
                has_transcript = frame.evaluate(r"""() => {
                    const segs = Array.from(document.querySelectorAll('.transcript-segment, .player__transcript-body p'))
                        .map(p => p.textContent.trim()).filter(Boolean);
                    return segs.join(' ').length > 20;
                }""")
                if has_transcript:
                    return []
            except Exception:
                pass
        
        # 2. Localizar el reproductor de audio de la pantalla activa visible
        matched_urls = []
        for frame in frames_to_check:
            try:
                scan_res = frame.evaluate(r"""() => {
                    const $ = window.jQuery;
                    if (!$) return null;
                    let $active = $('.content-wrap:visible, .activity:visible').first();
                    if ($active.length === 0) {
                        $active = $('.content-wrap, .activity').filter(function() { return $(this).css('display') !== 'none'; }).first();
                    }
                    if ($active.length === 0) return null;
                    
                    // En ejercicios de Speaking, priorizar el reproductor de audio del enunciado sobre las opciones
                    let $player = $active.find('.contentblock--SpeakingAndRecording > p .playbutton, .playbutton:not(.isRadiobuttonVoice__item .playbutton)');
                    if ($player.length === 0) {
                        $player = $active.find('.player, .audio, audio, [data-playable-media], .playbutton, .audio-player');
                    }
                    if ($player.length === 0) return { hasAudio: false };
                    
                    const hints = new Set();
                    const matched = [];
                    const baseUrl = (window.location.href || '').split('/index')[0];

                    $player.each(function() {
                        const aria = $(this).attr('aria-label') || '';
                        const dataPlayable = $(this).attr('data-playable-media') || '';
                        const src = $(this).attr('src') || $(this).find('source').attr('src') || $(this).attr('data-src') || '';
                        
                        const matches = (aria + ' ' + dataPlayable + ' ' + src + ' ' + $(this).html()).match(/[\w\-\.]+\.mp3/gi);
                        if (matches) {
                            matches.forEach(m => hints.add(m.toLowerCase()));
                        }
                        if (dataPlayable) {
                            const cleaned = dataPlayable.replace(/^ID_/, '').replace(/_\d+$/, '');
                            hints.add(cleaned.toLowerCase());
                            if (baseUrl) {
                                const direct = baseUrl + '/media/' + cleaned + '.mp3';
                                if (!matched.includes(direct)) matched.push(direct);
                            }
                        }
                        if (src && !matched.includes(src)) {
                            hints.add(src);
                            matched.push(src);
                        }
                    });
                    
                    const allMp3s = (window.performance && window.performance.getEntriesByType)
                        ? window.performance.getEntriesByType('resource')
                            .filter(r => r.name.includes('.mp3') && !r.name.includes('slime-sound') && !r.name.includes('correct') && !r.name.includes('wrong'))
                            .map(r => r.name)
                        : [];
                        
                    for (let url of allMp3s) {
                        const lower = url.toLowerCase();
                        for (let hint of hints) {
                            if (lower.includes(hint) || (hint.endsWith('.mp3') && lower.includes(hint.replace('.mp3', '')))) {
                                if (!matched.includes(url)) matched.push(url);
                                break;
                            }
                        }
                    }
                    
                    // Fallback: si hay reproductor pero no coincidió por nombre, tomar el último audio cargado
                    if (matched.length === 0 && allMp3s.length > 0) {
                        matched.push(allMp3s[allMp3s.length - 1]);
                    }
                    
                    return {
                        hasAudio: true,
                        matchedUrls: matched
                    };
                }""")
                if scan_res and scan_res.get('hasAudio'):
                    matched_urls = scan_res.get('matchedUrls', [])
                    if matched_urls:
                        break
            except Exception:
                pass
                
        if not matched_urls:
            return []
            
        # 3. Descargar ÚNICAMENTE los audios de la pantalla activa (máximo 2 audios)
        audio_files = []
        for url in matched_urls[:2]:
            try:
                response = context.request.get(url, timeout=15000)
                if response.ok:
                    audio_data = response.body()
                    b64_audio = base64.b64encode(audio_data).decode('utf-8')
                    audio_files.append({
                        "mime_type": "audio/mp3",
                        "data": b64_audio
                    })
            except Exception as e:
                print(f"Error downloading audio {url}: {e}")
                
        return audio_files
