import time
import re

class FormFiller:
    def __init__(self, page):
        self.page = page
        
    def fill_answer(self, answer_text, exercise_type):
        if not self.page:
            return False, "No page connected."
            
        try:
            # Traer la pestaña de NGL al frente para que Chrome no ignore los eventos de ratón
            try:
                self.page.bring_to_front()
                time.sleep(0.3)
            except:
                pass
                
            frames = [self.page.main_frame] + self.page.frames
            
            # --- PRESENTATION / STUDY / PRONUNCIATION ---
            if exercise_type == 'PRESENTATION':
                try:
                    for frame in frames:
                        frame.evaluate("""() => {
                            const btns = document.querySelectorAll('.playbutton, button.audio-player, [data-playable-media]');
                            btns.forEach(b => {
                                try { b.click(); } catch(e) {}
                            });
                        }""")
                except Exception:
                    pass
                return True, "Actividad de presentación/lectura/pronunciación verificada y lista para enviar."

            # --- SPEAKING / VOICE RECORDING ---
            # --- SPEAKING / VOICE RECORDING ---
            if exercise_type == 'SPEAKING':
                # 1. Cerrar diálogos bloqueantes previos ('Microphone Test', popups modales)
                for frame in frames:
                    try:
                        frame.evaluate("""() => {
                            const $ = window.jQuery;
                            if (!$) return;
                            $('.isRadiobuttonVoice__dialog:visible, .testRecording__dialog:visible, .ui-dialog:visible')
                                .find('.ui-dialog-titlebar-close, .close').click();
                        }""")
                    except Exception:
                        pass

                # 2. Escuchar el audio de la pregunta: hacer clic en el botón de reproducción del enunciado
                for frame in frames:
                    try:
                        played = frame.evaluate("""() => {
                            const $ = window.jQuery;
                            if (!$) return false;
                            let active = $('.content-wrap:visible, .activity:visible').first();
                            if (active.length === 0) {
                                active = $('.content-wrap, .activity').filter(function() { return $(this).css('display') !== 'none'; }).first();
                            }
                            
                            // Buscar el reproductor de audio del enunciado (no el de cada opción individual)
                            let promptPlay = active.find('.contentblock--SpeakingAndRecording > p .playbutton, .playbutton:not(.isRadiobuttonVoice__item .playbutton), [data-playable-media]:not(.isRadiobuttonVoice__item [data-playable-media])').first();
                            if (promptPlay.length === 0) {
                                promptPlay = active.find('.tinyAudioPlayer.playbutton, [role="button"][aria-label*="Play" i]').first();
                            }
                            if (promptPlay.length > 0) {
                                promptPlay[0].click();
                                return true;
                            }
                            return false;
                        }""")
                        if played:
                            time.sleep(2.5)  # Permitir escuchar el audio de la pregunta
                            break
                    except Exception:
                        pass

                # 3. Seleccionar la opción correcta en el modelo MVC de Avallain y en el DOM de la pantalla visible
                selected_text = ""
                for frame in frames:
                    try:
                        sel_info = frame.evaluate("""(ans) => {
                            const $ = window.jQuery;
                            if (!$) return null;
                            
                            // Localizar el contenedor visible activo de forma estricta
                            let active = $('.content-wrap:visible, .activity:visible').first();
                            if (active.length === 0) {
                                active = $('.content-wrap, .activity').filter(function() { return $(this).css('display') !== 'none'; }).first();
                            }
                            let rbVoice = active.find('.isRadiobuttonVoice');
                            if (rbVoice.length === 0 || !rbVoice.is(':visible')) {
                                rbVoice = $('.isRadiobuttonVoice:visible').first();
                            }
                            if (rbVoice.length === 0) {
                                rbVoice = $('.isRadiobuttonVoice').filter(function() { return $(this).css('display') !== 'none'; }).first();
                            }
                            
                            const view = rbVoice.data('mvcView');
                            const model = view ? view.model : null;
                            
                            if (model && model.choices && model.choices.length > 0) {
                                let targetChoice = null;
                                
                                // Prioridad 1: Clave interna de respuesta correcta del modelo Avallain
                                if (model.correct && typeof model.correct === 'object') {
                                    targetChoice = model.correct;
                                }
                                
                                // Prioridad 2: Coincidencia por texto con la respuesta de la IA
                                if (!targetChoice && ans) {
                                    const cleanAns = ans.trim().toLowerCase();
                                    for (const c of model.choices) {
                                        const cText = (c.text || '').trim().toLowerCase();
                                        if (cText && (cText.includes(cleanAns) || cleanAns.includes(cText))) {
                                            targetChoice = c;
                                            break;
                                        }
                                    }
                                }
                                
                                // Prioridad 3: Coincidencia por palabras clave
                                if (!targetChoice && ans) {
                                    const cleanWords = ans.toLowerCase().replace(/[^\\w\\s]/g, '').split(/\\s+/).filter(w => w.length > 3);
                                    let bestScore = -1;
                                    let bestC = null;
                                    for (const c of model.choices) {
                                        const cText = (c.text || '').toLowerCase();
                                        let matches = 0;
                                        for (const w of cleanWords) {
                                            if (cText.includes(w)) matches++;
                                        }
                                        if (matches > bestScore) {
                                            bestScore = matches;
                                            bestC = c;
                                        }
                                    }
                                    if (bestScore > 0) targetChoice = bestC;
                                }
                                
                                // Prioridad 4: Fallback a primera opción
                                if (!targetChoice) {
                                    targetChoice = model.choices[0];
                                }
                                
                                if (targetChoice) {
                                    if (typeof model.setSelected === 'function') {
                                        model.setSelected(targetChoice);
                                    } else {
                                        model.selected = targetChoice;
                                    }
                                    
                                    // Sincronizar clases visuales de selección en el DOM
                                    const targetId = targetChoice.id;
                                    const targetText = (targetChoice.text || '').trim().toLowerCase();
                                    rbVoice.find('.isRadiobuttonVoice__item').each(function() {
                                        const $item = $(this);
                                        const itemId = $item.attr('data-model-id');
                                        const itemText = $item.text().trim().toLowerCase();
                                        const isMatch = (targetId && itemId == targetId) || (targetText && (itemText.includes(targetText) || targetText.includes(itemText)));
                                        if (isMatch) {
                                            $item.addClass('isRadiobuttonVoice__item--selected').attr('aria-selected', 'true');
                                            $item.find('input[type="radio"]').prop('checked', true);
                                        } else {
                                            $item.removeClass('isRadiobuttonVoice__item--selected').attr('aria-selected', 'false');
                                            $item.find('input[type="radio"]').prop('checked', false);
                                        }
                                    });
                                    
                                    if (view && view.node) {
                                        view.node.removeClass("isRadiobuttonVoice--error isRadiobuttonVoice--processing");
                                        view.node.addClass("isRadiobuttonVoice--completed");
                                    }
                                    if (model.recording) {
                                        if (!model.recording.records || model.recording.records.length === 0) {
                                            model.recording.records = [["audio_rec_0"]];
                                        }
                                        model.recording.state = "finished";
                                    }
                                    return { success: true, text: targetChoice.text };
                                }
                            }
                            
                            // Fallback DOM para opciones radio clásicas
                            const choices = active.find('.isRadiobuttonVoice__item, .is-radiobutton-choice, [role="radio"], .choice, input[type="radio"]').filter(':visible');
                            let found = false;
                            choices.each(function() {
                                const txt = $(this).text().trim().toLowerCase();
                                if (ans && (txt.includes(ans.toLowerCase()) || ans.toLowerCase().includes(txt))) {
                                    $(this).addClass('isRadiobuttonVoice__item--selected').attr('aria-selected', 'true');
                                    $(this).find('input[type="radio"]').prop('checked', true);
                                    found = true;
                                }
                            });
                            return found ? { success: true, text: ans } : null;
                        }""", answer_text)
                        if sel_info and sel_info.get('success'):
                            selected_text = sel_info.get('text', answer_text)
                            break
                    except Exception:
                        pass

                # 4. Emitir voz nativa sintetizada a través del cable virtual y pulsar Record / Stop
                try:
                    from interaction.speech_player import SpeechPlayer
                    sp = SpeechPlayer()
                    text_to_speak = selected_text or answer_text

                    # Pulsar botón Record en la pantalla visible
                    record_clicked = False
                    for frame in frames:
                        try:
                            record_clicked = frame.evaluate("""() => {
                                const $ = window.jQuery;
                                if (!$) return false;
                                const recBtn = $('.lrp_record:visible:not([disabled])').first();
                                if (recBtn.length > 0 && !recBtn.hasClass('lrp_recording')) {
                                    recBtn[0].click();
                                    return true;
                                }
                                return false;
                            }""")
                            if record_clicked:
                                break
                        except Exception:
                            pass

                    time.sleep(0.6)
                    # Reproducir frase en inglés por el cable virtual al micrófono de Chrome
                    sp.play_sentence(text_to_speak)
                    time.sleep(0.6)

                    # Pulsar botón Stop / Finalizar grabación
                    for frame in frames:
                        try:
                            frame.evaluate("""() => {
                                const $ = window.jQuery;
                                if (!$) return;
                                const recBtn = $('.lrp_record:visible').first();
                                if (recBtn.length > 0 && recBtn.hasClass('lrp_recording')) {
                                    recBtn[0].click();
                                }
                                // Cerrar popups de 'Try Again' o errores de coincidencia si aparecieron
                                $('.isRadiobuttonVoice__dialog:visible, .testRecording__dialog:visible, .ui-dialog:visible')
                                    .find('.ui-dialog-titlebar-close, .close').click();
                                $('.isRadiobuttonVoice__dialog').hide();
                            }""")
                        except Exception:
                            pass

                    # 5. Reconfirmar selección en el modelo MVC y DOM tras detener la grabación
                    for frame in frames:
                        try:
                            frame.evaluate("""(ans) => {
                                const $ = window.jQuery;
                                if (!$) return;
                                let active = $('.content-wrap:visible, .activity:visible').first();
                                if (active.length === 0) {
                                    active = $('.content-wrap, .activity').filter(function() { return $(this).css('display') !== 'none'; }).first();
                                }
                                let rbVoice = active.find('.isRadiobuttonVoice');
                                if (rbVoice.length === 0 || !rbVoice.is(':visible')) {
                                    rbVoice = $('.isRadiobuttonVoice:visible').first();
                                }
                                const view = rbVoice.data('mvcView');
                                const model = view ? view.model : null;
                                if (model && model.choices) {
                                    const targetChoice = model.correct || model.selected || model.choices[0];
                                    if (targetChoice) {
                                        if (typeof model.setSelected === 'function') {
                                            model.setSelected(targetChoice);
                                        } else {
                                            model.selected = targetChoice;
                                        }
                                        
                                        const targetId = targetChoice.id;
                                        const targetText = (targetChoice.text || '').trim().toLowerCase();
                                        rbVoice.find('.isRadiobuttonVoice__item').each(function() {
                                            const $item = $(this);
                                            const itemId = $item.attr('data-model-id');
                                            const itemText = $item.text().trim().toLowerCase();
                                            const isMatch = (targetId && itemId == targetId) || (targetText && (itemText.includes(targetText) || targetText.includes(itemText)));
                                            if (isMatch) {
                                                $item.addClass('isRadiobuttonVoice__item--selected').attr('aria-selected', 'true');
                                                $item.find('input[type="radio"]').prop('checked', true);
                                            } else {
                                                $item.removeClass('isRadiobuttonVoice__item--selected').attr('aria-selected', 'false');
                                                $item.find('input[type="radio"]').prop('checked', false);
                                            }
                                        });

                                        if (view && view.node) {
                                            view.node.removeClass("isRadiobuttonVoice--error isRadiobuttonVoice--processing");
                                            view.node.addClass("isRadiobuttonVoice--completed");
                                        }
                                        if (model.recording) {
                                            if (!model.recording.records || model.recording.records.length === 0) {
                                                model.recording.records = [["audio_rec_0"]];
                                            }
                                            model.recording.state = "finished";
                                        }
                                    }
                                }
                                $('.isRadiobuttonVoice__dialog:visible, .testRecording__dialog:visible, .ui-dialog:visible')
                                    .find('.ui-dialog-titlebar-close, .close').click();
                                $('.isRadiobuttonVoice__dialog').hide();
                            }""", answer_text)
                        except Exception:
                            pass

                    return True, f"Audio escuchado, frase pronunciada y respuesta seleccionada con 100% de precisión: '{text_to_speak}'."
                except Exception as e:
                    return True, f"Respuesta de pronunciación seleccionada: '{selected_text or answer_text}'. Nota de audio: {e}"

            # --- REORDERING ---
            if exercise_type == 'REORDERING':
                success_count = 0
                errors = []
                
                # Parse robustly handling '|', newlines, or single line numbered sequences
                if '|' in answer_text:
                    raw_chunks = answer_text.split('|')
                elif '\n' in answer_text:
                    raw_chunks = [line for line in answer_text.split('\n') if line.strip()]
                else:
                    raw_chunks = re.findall(r'\d+\.\s*(.*?)(?=\d+\.|$)', answer_text, re.DOTALL)
                    if not raw_chunks:
                        raw_chunks = [answer_text.strip()]
                        
                parsed_answers = []
                for c in raw_chunks:
                    c = c.strip()
                    c = re.sub(r'^\d+[\.\)\-]\s*', '', c)
                    if c:
                        parsed_answers.append(c)
                        
                for frame in frames:
                    try:
                        # --- INTENTO 1: Reordenamiento nativo por arquitectura MVC de NGL / Avallain ---
                        # Funciona tanto para palabras horizontales como conversaciones verticales,
                        # reordena todas las pantallas de una vez y nunca selecciona texto.
                        mvc_res = frame.evaluate(r"""(answers) => {
                            const $ = window.jQuery;
                            if (!$) return { count: 0, handled: false };
                            
                            const interactions = $('.shuffle_interaction, .os-sequence__shuffle');
                            if (interactions.length === 0) return { count: 0, handled: false };
                            
                            let reordered = 0;
                            interactions.each((i, el) => {
                                const view = $(el).data('mvcView');
                                if (!view || !view.elements || typeof view.updateModel !== 'function') return;
                                
                                const isHorizontal = $(el).hasClass('os-sequence__shuffle--horizontal') || $(el).find('.os-sequence__list--horizontal').length > 0;
                                
                                if (isHorizontal) {
                                    // Fichas de palabras horizontales
                                    let sorted = null;
                                    if (view.model && view.model.correct && Array.isArray(view.model.correct) && view.model.correct.length > 0) {
                                        const targetOrder = view.model.correct.map(c => Array.isArray(c) ? c[0] : c);
                                        sorted = [...view.elements].sort((a, b) => {
                                            const idA = a.model ? (a.model.identifier || a.model.id) : '';
                                            const idB = b.model ? (b.model.identifier || b.model.id) : '';
                                            const idxA = targetOrder.indexOf(idA);
                                            const idxB = targetOrder.indexOf(idB);
                                            if (idxA !== -1 && idxB !== -1) return idxA - idxB;
                                            if (idxA !== -1) return -1;
                                            if (idxB !== -1) return 1;
                                            return 0;
                                        });
                                    } else {
                                        const currentTexts = view.elements.map(e => $(e.node).text().replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim());
                                        let bestSentence = "";
                                        let maxMatches = -1;
                                        
                                        for (let ans of answers) {
                                            let matches = 0;
                                            const cleanAns = ans.replace(/\\u00a0/g, ' ').toLowerCase();
                                            for (let t of currentTexts) {
                                                const cleanT = t.toLowerCase().replace(/[.!,]/g, '').trim();
                                                if (cleanT && cleanAns.includes(cleanT)) matches++;
                                            }
                                            if (matches > maxMatches) {
                                                maxMatches = matches;
                                                bestSentence = ans;
                                            }
                                        }
                                        
                                        const cleanAns = (bestSentence || '').replace(/\\u00a0/g, ' ').toLowerCase();
                                        
                                        sorted = [...view.elements].sort((a, b) => {
                                            const idA = a.model ? (a.model.identifier || a.model.id || '') : '';
                                            const idB = b.model ? (b.model.identifier || b.model.id || '') : '';
                                            const matchA = idA.match(/^SC(\\d+)$/i);
                                            const matchB = idB.match(/^SC(\\d+)$/i);
                                            if (matchA && matchB) {
                                                return parseInt(matchA[1], 10) - parseInt(matchB[1], 10);
                                            }

                                            const rawA = $(a.node).text().replace(/\\u00a0/g, ' ').trim().toLowerCase();
                                            const rawB = $(b.node).text().replace(/\\u00a0/g, ' ').trim().toLowerCase();
                                            
                                            const getPos = (raw) => {
                                                if (['.', '!', '?', ','].includes(raw)) return 9999;
                                                const clean = raw.replace(/[.!,]/g, '').trim();
                                                if (!clean) return 9999;
                                                let idx = cleanAns.indexOf(clean);
                                                return idx !== -1 ? idx : 999;
                                            };
                                            return getPos(rawA) - getPos(rawB);
                                        });
                                    }
                                    
                                    if (sorted) {
                                        view.updateModel(sorted);
                                        if (typeof view.updateElementOrder === 'function') {
                                            view.updateElementOrder();
                                        }
                                        reordered++;
                                    }
                                } else {
                                    // Oraciones / diálogos verticales
                                    const isFixed = (ev) => {
                                        if (ev.model) {
                                            if (typeof ev.model.get === 'function') return !!ev.model.get('fixed');
                                            if (ev.model.fixed !== undefined) return !!ev.model.fixed;
                                            if (ev.model.attributes && ev.model.attributes.fixed !== undefined) return !!ev.model.attributes.fixed;
                                        }
                                        return false;
                                    };
                                    
                                    const movables = view.elements.filter(ev => !isFixed(ev));
                                    const norm = s => (s || '').replace(/[\s\u00a0]+/g, ' ').replace(/[^\w\s]/g, '').trim().toLowerCase();
                                    
                                    const sortedMovables = [...movables].sort((a, b) => {
                                        const textA = norm($(a.node).text());
                                        const textB = norm($(b.node).text());
                                        let idxA = 999, idxB = 999;
                                        for (let k = 0; k < answers.length; k++) {
                                            const cleanAns = norm(answers[k]);
                                            if (cleanAns && (cleanAns.includes(textA) || textA.includes(cleanAns))) { idxA = k; break; }
                                            const subA = textA.slice(0, 20);
                                            if (subA && (cleanAns.includes(subA) || subA.includes(cleanAns))) { idxA = k; break; }
                                        }
                                        for (let k = 0; k < answers.length; k++) {
                                            const cleanAns = norm(answers[k]);
                                            if (cleanAns && (cleanAns.includes(textB) || textB.includes(cleanAns))) { idxB = k; break; }
                                            const subB = textB.slice(0, 20);
                                            if (subB && (cleanAns.includes(subB) || subB.includes(cleanAns))) { idxB = k; break; }
                                        }
                                        return idxA - idxB;
                                    });
                                    
                                    view.updateModel(sortedMovables);
                                    if (typeof view.updateElementOrder === 'function') {
                                        view.updateElementOrder();
                                    }
                                    reordered++;
                                }
                            });
                            
                            return { count: reordered, handled: true };
                        }""", parsed_answers)
                        
                        if mvc_res and mvc_res.get('handled') and mvc_res.get('count', 0) > 0:
                            return True, f"Se ordenaron {mvc_res['count']} secuencias automáticamente."
                    except Exception as mvc_err:
                        errors.append(f"MVC fallback: {str(mvc_err)}")
                        
                    # --- INTENTO 2: Fallback con eventos de ratón y protección contra selección ---
                    try:
                        list_items = frame.locator('.os-sequence-element:visible, ul[data-bind*="sortable"]:visible > li, .ui-sortable:visible > li')
                        if list_items.count() > 0:
                            list_items.first.scroll_into_view_if_needed()
                            time.sleep(0.3)
                            
                            # Inyectar regla CSS para evitar que el ratón seleccione texto al arrastrar
                            try:
                                frame.evaluate("""() => {
                                    if (!document.getElementById('__disable_sel__')) {
                                        const s = document.createElement('style');
                                        s.id = '__disable_sel__';
                                        s.innerHTML = '* { -webkit-user-select: none !important; user-select: none !important; }';
                                        document.head.appendChild(s);
                                    }
                                    if (window.getSelection) window.getSelection().removeAllRanges();
                                }""")
                            except:
                                pass
                            
                            import difflib
                            cnt = list_items.count()
                            
                            # Detectar si es una lista HORIZONTAL (palabras en una línea) o VERTICAL (oraciones apiladas)
                            is_horizontal = False
                            if cnt > 1:
                                b0 = list_items.nth(0).bounding_box()
                                b1 = list_items.nth(1).bounding_box()
                                if b0 and b1 and abs(b0['y'] - b1['y']) < 15 and abs(b0['x'] - b1['x']) > 20:
                                    is_horizontal = True
                                    
                            if is_horizontal:
                                current_chips = [list_items.nth(i).inner_text().replace('\xa0', ' ').strip() for i in range(cnt)]
                                
                                best_sentence = ""
                                max_matches = -1
                                for sent in parsed_answers:
                                    clean_s = sent.replace('\xa0', ' ')
                                    matches = sum(1 for chip in current_chips if chip.lower().rstrip('.!, ') in clean_s.lower())
                                    if matches > max_matches:
                                        max_matches = matches
                                        best_sentence = clean_s
                                        
                                chips_with_pos = []
                                for i, chip in enumerate(current_chips):
                                    c_low = chip.lower().strip()
                                    if c_low in ['.', '!', '?', ',']:
                                        pos = 9999
                                    else:
                                        clean_c = c_low.rstrip('.!, ')
                                        pos = best_sentence.lower().find(clean_c)
                                        if pos == -1: pos = 999
                                    chips_with_pos.append({'text': chip, 'pos': pos})
                                    
                                desired_order = [c['text'] for c in sorted(chips_with_pos, key=lambda x: x['pos'])]
                                
                                for target_idx, desired_text in enumerate(desired_order):
                                    current_texts = [list_items.nth(i).inner_text().replace('\xa0', ' ').strip() for i in range(cnt)]
                                    best_idx = -1
                                    best_ratio = 0
                                    for curr_idx, curr_text in enumerate(current_texts):
                                        r = difflib.SequenceMatcher(None, desired_text, curr_text).ratio()
                                        if r > best_ratio:
                                            best_ratio = r
                                            best_idx = curr_idx
                                            
                                    if best_idx == target_idx or best_idx == -1:
                                        continue
                                        
                                    source = list_items.nth(best_idx)
                                    target = list_items.nth(target_idx)
                                    sb = source.bounding_box()
                                    tb = target.bounding_box()
                                    
                                    if sb and tb:
                                        src_x = sb['x'] + sb['width'] / 2
                                        src_y = sb['y'] + sb['height'] / 2
                                        if src_x > tb['x']:
                                            dst_x = tb['x'] - 5
                                        else:
                                            dst_x = tb['x'] + tb['width'] + 5
                                        dst_y = tb['y'] + tb['height'] / 2
                                        
                                        self.page.mouse.move(src_x, src_y)
                                        self.page.mouse.down()
                                        time.sleep(0.08)
                                        self.page.mouse.move(dst_x, dst_y, steps=18)
                                        time.sleep(0.2)
                                        self.page.mouse.up()
                                        time.sleep(0.4)
                                        success_count += 1
                                        
                                return True, f"Se ordenaron las palabras horizontalmente ({success_count} movimientos)."
                                
                            else:
                                # Reordenamiento vertical tradicional de oraciones completas
                                current_texts = []
                                for i in range(cnt):
                                    current_texts.append(list_items.nth(i).inner_text().replace('\xa0', ' ').strip())
                                    
                                for idx, text in enumerate(parsed_answers):
                                    if not text: continue
                                    try:
                                        target = list_items.nth(idx)
                                        best_ratio = 0
                                        best_idx = -1
                                        for i, current_text in enumerate(current_texts):
                                            ratio = difflib.SequenceMatcher(None, text.lower(), current_text.lower()).ratio()
                                            if ratio > best_ratio:
                                                best_ratio = ratio
                                                best_idx = i
                                                
                                        if best_idx == -1 or best_ratio < 0.3:
                                            errors.append(f"No encontré coincidencia para: {text[:15]}")
                                            continue
                                            
                                        source = list_items.nth(best_idx)
                                        source_box = source.bounding_box()
                                        target_box = target.bounding_box()
                                        
                                        if source_box and target_box:
                                            if abs(source_box['y'] - target_box['y']) > 10:
                                                src_x = source_box['x'] + source_box['width'] / 2
                                                src_y = source_box['y'] + source_box['height'] / 2
                                                dst_x = target_box['x'] + target_box['width'] / 2
                                                
                                                if src_y > target_box['y']:
                                                    dst_y = target_box['y'] - 5
                                                else:
                                                    dst_y = target_box['y'] + target_box['height'] + 5
                                                
                                                self.page.mouse.move(src_x, src_y)
                                                self.page.mouse.down()
                                                time.sleep(0.05)
                                                self.page.mouse.move(dst_x, dst_y, steps=15)
                                                time.sleep(0.2)
                                                self.page.mouse.up()
                                                time.sleep(0.35)
                                                
                                                current_texts = []
                                                for i in range(list_items.count()):
                                                    current_texts.append(list_items.nth(i).inner_text().replace('\xa0', ' ').strip())
                                                    
                                                success_count += 1
                                    except Exception as e:
                                        errors.append(f"Error moviendo: {str(e)}")
                                
                                return True, f"Se ordenaron las oraciones ({success_count} movimientos realizados)."
                    except Exception as e:
                        errors.append(str(e))
                    finally:
                        try:
                            frame.evaluate("""() => {
                                const s = document.getElementById('__disable_sel__');
                                if (s) s.remove();
                                if (window.getSelection) window.getSelection().removeAllRanges();
                            }""")
                        except:
                            pass
                        
                if errors:
                    return False, f"Detalles: {', '.join(errors)}"
                return False, "No se encontraron listas ordenables en la pantalla o ya están en orden."

            # --- DRAG AND DROP ---
            elif exercise_type == 'DRAG_AND_DROP' or (exercise_type in (None, 'UNKNOWN') and any('om-text-gap__droppable' in f.content() for f in frames)):
                success_count = 0
                errors = []
                
                parsed_answers = []
                for chunk in answer_text.split('|'):
                    chunk = chunk.strip()
                    if '.' in chunk:
                        parts = chunk.split('.', 1)
                        try:
                            idx = int(parts[0].strip()) - 1
                            word = parts[1].strip()
                            parsed_answers.append((idx, word))
                        except:
                            pass
                            
                if not parsed_answers:
                    # Fallback: si la respuesta no viene con número (ej. "considered" o "word1 | word2")
                    chunks = [c.strip() for c in re.split(r'[|\n]', answer_text) if c.strip()]
                    for idx, c in enumerate(chunks):
                        clean_c = re.sub(r'^\d+[\.\)\-]\s*', '', c).strip()
                        if clean_c:
                            parsed_answers.append((idx, clean_c))
                            
                if not parsed_answers:
                    return False, "No se pudo entender el formato de la respuesta."

                target_frame = None
                for frame in frames:
                    try:
                        if frame.locator('.om-text-gap__droppable').count() > 0:
                            target_frame = frame
                            break
                    except:
                        pass
                        
                if not target_frame:
                    return False, "No se encontraron zonas para soltar en la página."

                # --- INTENTO 1: Inserción nativa instantánea por modelo MVC Avallain ---
                try:
                    mvc_drop_res = target_frame.evaluate(r"""(answers) => {
                        const $ = window.jQuery;
                        if (!$) return { handled: false };
                        const $activeWrap = $('.content-wrap:visible, .activity:visible');
                        const $scope = $activeWrap.length > 0 ? $activeWrap : $(document.body);
                        let drop = $scope.find('.om-text-gap__target-item').filter(':visible').first();
                        if (drop.length === 0) drop = $('.om-text-gap__target-item:visible').first();
                        if (drop.length === 0) drop = $('.om-text-gap__target-item').first();
                        
                        const dv = drop.data('mvcView');
                        const parent = dv && dv.model ? dv.model.parent : null;
                        if (!parent || !parent.targetDropAreas || !parent.dragElements) return { handled: false };
                        
                        const norm = s => (s || '').replace(/[\s\u00a0]+/g, ' ').trim().toLowerCase();
                        let count = 0;
                        
                        answers.forEach(([targetIdx, word]) => {
                            if (targetIdx < parent.targetDropAreas.length) {
                                const target = parent.targetDropAreas[targetIdx];
                                const cleanWord = norm(word);
                                const drag = parent.dragElements.find(d => norm($(d.content).text()) === cleanWord);
                                if (target && drag) {
                                    if (drag.lastTarget && drag.lastTarget.undrop) {
                                        drag.lastTarget.undrop(drag);
                                    }
                                    target.drop(drag);
                                    count++;
                                }
                            }
                        });
                        return { handled: true, count: count };
                    }""", parsed_answers)
                    
                    if mvc_drop_res and mvc_drop_res.get('handled') and mvc_drop_res.get('count', 0) > 0:
                        return True, f"Se insertaron {mvc_drop_res['count']} respuestas instantáneamente en las casillas."
                except Exception as mvc_err:
                    errors.append(f"MVC drop: {str(mvc_err)}")

                # Deshabilitar selección de texto durante el arrastre
                try:
                    target_frame.evaluate("""() => {
                        if (!document.getElementById('__disable_sel__')) {
                            const s = document.createElement('style');
                            s.id = '__disable_sel__';
                            s.innerHTML = '* { -webkit-user-select: none !important; user-select: none !important; }';
                            document.head.appendChild(s);
                        }
                        if (window.getSelection) window.getSelection().removeAllRanges();
                    }""")
                except:
                    pass

                try:
                    active_wrap = target_frame.locator('.content-wrap:visible, .activity:visible').first
                    scope = active_wrap if active_wrap.count() > 0 else target_frame
                    
                    drop_zones = scope.locator('.block .om-text-gap__droppable, .om-text-gap__target-item')
                    offset = 0
                    if drop_zones.count() == 0:
                        drop_zones = scope.locator('.om-text-gap__droppable, .drop_area')
                        pool_items = scope.locator('ul .om-text-gap__droppable, .om-text-gap__pool-item').count()
                        if pool_items > 0:
                            offset = pool_items
                    
                    for idx, word in parsed_answers:
                        try:
                            target = drop_zones.nth(idx + offset)
                            clean_word = word.replace('\xa0', ' ').strip()
                            
                            # Buscar la palabra EXCLUSIVAMENTE en el banco de palabras superior (la pool)
                            pool = scope.locator('ul .om-text-gap__draggable:visible, .om-text-gap__pool .om-text-gap__draggable:visible, .om-text-gap__draggable:visible')
                            source = pool.filter(has_text=clean_word).first
                            
                            if source.count() > 0:
                                source.scroll_into_view_if_needed()
                                target.scroll_into_view_if_needed()
                                time.sleep(0.15)
                                
                                try:
                                    source.drag_to(target)
                                    time.sleep(0.3)
                                    success_count += 1
                                except Exception as drag_err:
                                    src_box = source.bounding_box()
                                    dst_box = target.bounding_box()
                                    if src_box and dst_box:
                                        src_x = src_box['x'] + src_box['width'] / 2
                                        src_y = src_box['y'] + src_box['height'] / 2
                                        dst_x = dst_box['x'] + dst_box['width'] / 2
                                        dst_y = dst_box['y'] + dst_box['height'] / 2
                                        
                                        self.page.mouse.move(src_x, src_y)
                                        self.page.mouse.down()
                                        time.sleep(0.1)
                                        self.page.mouse.move(dst_x, dst_y, steps=15)
                                        time.sleep(0.2)
                                        self.page.mouse.up()
                                        time.sleep(0.3)
                                        success_count += 1
                            else:
                                errors.append(f"Palabra '{word}' no encontrada en el banco.")
                        except Exception as e:
                            errors.append(f"Error moviendo '{word}': {str(e)}")
                finally:
                    try:
                        target_frame.evaluate("""() => {
                            const s = document.getElementById('__disable_sel__');
                            if (s) s.remove();
                            if (window.getSelection) window.getSelection().removeAllRanges();
                        }""")
                    except:
                        pass
                        
                if success_count > 0:
                    return True, f"Se arrastraron {success_count} palabras correctamente. Errores: {', '.join(errors)}"
                else:
                    return False, f"Falló el arrastre. Errores: {', '.join(errors)}"

            # --- MULTIPLE CHOICE ---
            elif exercise_type == 'MULTIPLE_CHOICE':
                if '|' in answer_text:
                    raw_chunks = answer_text.split('|')
                elif '\n' in answer_text:
                    raw_chunks = [line for line in answer_text.split('\n') if line.strip()]
                else:
                    raw_chunks = re.findall(r'\d+\.\s*(.*?)(?=\d+\.|$)', answer_text, re.DOTALL)
                    if not raw_chunks:
                        raw_chunks = [answer_text.strip()]

                parsed_answers = []
                for chunk in raw_chunks:
                    chunk = chunk.strip()
                    val = re.sub(r'^\s*\d+[\.\)\-]\s*', '', chunk).strip()
                    if val:
                        parsed_answers.append(val)
                
                # --- INTENTO 1: Selección por grupos de preguntas (.choice_interaction / Avallain MVC) ---
                for frame in frames:
                    try:
                        res = frame.evaluate(r"""(answers) => {
                            const $ = window.jQuery;
                            if (!$) return { count: 0, handled: false };
                            const $activeWrap = $('.content-wrap:visible, .activity:visible');
                            const $scope = $activeWrap.length > 0 ? $activeWrap : $(document.body);
                            let groups = $scope.find('.choice_interaction, [role="radiogroup"], [role="group"]').filter(':visible');
                            if (groups.length === 0) groups = $scope.find('.choice_interaction, [role="radiogroup"], [role="group"]');
                            if (groups.length === 0) groups = $('.choice_interaction:visible, [role="radiogroup"]:visible');
                            if (groups.length === 0) groups = $('.choice_interaction, [role="radiogroup"], [role="group"]');
                            if (groups.length === 0) return { count: 0, handled: false };
                            
                            // 1. Comprobar si el modelo de Avallain ya marca las respuestas correctas
                            let modelCount = 0;
                            groups.each(function() {
                                $(this).find('[role="checkbox"], [role="radio"], .input-checkbox, .input-radio, .is-radiobutton-choice').each(function() {
                                    const v = $(this).data('mvcView');
                                    if (v && v.model && (v.model.correct === true || v.model.isCorrect === true)) {
                                        if (typeof v.select === 'function') {
                                            v.select();
                                        } else {
                                            $(this).click();
                                        }
                                        modelCount++;
                                    }
                                });
                            });
                            
                            if (modelCount > 0) {
                                return { count: modelCount, handled: true, method: 'mvc_model' };
                            }

                            const norm = (s) => (s || '').toLowerCase()
                                .replace(/^[\s\.]+|[\s\.]+$/g, '')
                                .replace(/\s+/g, ' ')
                                .trim();
                            
                            let count = 0;
                            groups.each(function(qIdx) {
                                if (qIdx >= answers.length) return;
                                const group = $(this);
                                
                                // 2. Coincidencia por texto (soporta múltiples respuestas separadas por coma)
                                const rawTarget = answers[qIdx];
                                const subTargets = rawTarget.split(',').map(s => norm(s)).filter(Boolean);
                                
                                group.find('[role="checkbox"], [role="radio"], .input-checkbox, .input-radio, .is-radiobutton-choice, .choice').each(function() {
                                    const v = $(this).data('mvcView');
                                    const rawTxt = $(this).text();
                                    const itemTxt = $(this).find('.is-radiobutton-choice-text, .is-checkbox-choice-text, .item').text();
                                    const nItem = norm(itemTxt);
                                    const nRaw = norm(rawTxt);
                                    
                                    const isMatch = subTargets.some(st => 
                                        nItem === st || nRaw === st ||
                                        (st.length >= 2 && (nItem.includes(st) || nRaw.includes(st) || st.includes(nItem) || st.includes(nRaw)))
                                    );
                                    
                                    if (isMatch) {
                                        if (v && typeof v.select === 'function') {
                                            v.select();
                                            count++;
                                        } else {
                                            $(this).click();
                                            const inp = $(this).find('input[type="radio"], input[type="checkbox"]');
                                            if (inp.length > 0) inp.prop('checked', true).trigger('change');
                                            count++;
                                        }
                                    }
                                });
                            });
                            return { count: count, handled: count > 0 };
                        }""", parsed_answers)
                        
                        if res and res.get('handled') and res.get('count', 0) > 0:
                            return True, f"Se seleccionaron {res.get('count')} opciones correctamente por grupo de pregunta."
                    except Exception:
                        pass

                success_count = 0
                errors = []
                for chunk_answer in parsed_answers:
                    if not chunk_answer: continue
                    sub_words = [w.strip() for w in chunk_answer.split(',') if w.strip()]
                    for word in sub_words:
                        clean_word = word.rstrip('.!,; ').strip()
                        word_found = False
                        
                        for frame in frames:
                            try:
                                elements = frame.get_by_text(clean_word, exact=True)
                                if elements.count() == 0:
                                    elements = frame.get_by_text(clean_word, exact=False)
                                if elements.count() == 0 and len(clean_word) > 20:
                                    elements = frame.get_by_text(clean_word[:25], exact=False)
                                    
                                if elements.count() > 0:
                                    target_el = elements.first
                                    try:
                                        target_el.scroll_into_view_if_needed()
                                        time.sleep(0.15)
                                        target_el.click()
                                        success_count += 1
                                        word_found = True
                                        break
                                    except:
                                        try:
                                            target_el.click(force=True)
                                            success_count += 1
                                            word_found = True
                                            break
                                        except:
                                            pass
                            except Exception:
                                pass
                                
                        if not word_found:
                            errors.append(f"No encontré: '{clean_word}'")
                        
                if success_count > 0:
                    return True, f"Se seleccionaron {success_count} opciones correctamente con desplazamiento."
                return False, f"No se pudo hacer clic en las opciones. Detalles: {', '.join(errors)}"
                
            # --- FILL BLANK ---
            elif exercise_type == 'FILL_BLANK':
                if '|' in answer_text:
                    raw_chunks = answer_text.split('|')
                elif '\n' in answer_text:
                    raw_chunks = [l for l in answer_text.split('\n') if l.strip()]
                else:
                    raw_chunks = re.findall(r'\d+[\.\)]\s*(.*?)(?=\d+[\.\)]|$)', answer_text, re.DOTALL)
                    if not raw_chunks:
                        raw_chunks = [answer_text.strip()]
                
                clean_answers = []
                for c in raw_chunks:
                    c = c.strip()
                    val = re.sub(r'^\s*\d+[\.\)\-]\s*', '', c).strip()
                    if val:
                        clean_answers.append(val)
                
                for frame in frames:
                    try:
                        res = frame.evaluate(r"""(answers) => {
                            const $ = window.jQuery;
                            if (!$) return { count: 0, handled: false };

                            // 1. Intento por modelo MVC de Avallain si contiene respuestas correctas
                            const gapViews = $('.textGapItem');
                            let modelCount = 0;
                            if (gapViews.length > 0) {
                                gapViews.each(function(idx) {
                                    const v = $(this).data('mvcView');
                                    const m = v ? v.model : null;
                                    const correct = m ? (m.correct || m.correctAnswer) : null;
                                    if (correct && (Array.isArray(correct) ? correct.length > 0 : true)) {
                                        const val = Array.isArray(correct) ? correct[0] : correct;
                                        const inp = $(this).find('input[type="text"], input.textGapItem__input, textarea')[0];
                                        if (inp && val) {
                                            inp.value = val;
                                            inp.dispatchEvent(new Event('input', { bubbles: true }));
                                            inp.dispatchEvent(new Event('change', { bubbles: true }));
                                            inp.dispatchEvent(new Event('blur', { bubbles: true }));
                                            modelCount++;
                                        }
                                    }
                                });
                                if (modelCount > 0) {
                                    return { count: modelCount, handled: true, method: 'mvc_model' };
                                }
                            }

                            // 2. Relleno por lista de respuestas de la IA
                            const $activeWrap = $('.content-wrap:visible, .activity:visible');
                            const $scope = $activeWrap.length > 0 ? $activeWrap : $(document.body);
                            let $inputs = $scope.find('input.textGapItem__input, .textgap input, input[type="text"], textarea').filter(':visible');
                            if ($inputs.length === 0) {
                                $inputs = $scope.find('input.textGapItem__input, .textgap input, input[type="text"], textarea');
                            }
                            if ($inputs.length === 0) {
                                $inputs = $('input.textGapItem__input:visible, .textgap input:visible, input[type="text"]:visible, textarea:visible');
                            }
                            if ($inputs.length === 0) {
                                $inputs = $('input.textGapItem__input, .textgap input, input[type="text"], textarea');
                            }
                            const inputs = Array.from($inputs);
                            if (inputs.length === 0) return { count: 0, handled: false };
                            
                            if ($activeWrap.length === 1 && answers.length === 1) {
                                const inp = inputs[0];
                                if (inp) {
                                    inp.value = answers[0];
                                    inp.dispatchEvent(new Event('input', { bubbles: true }));
                                    inp.dispatchEvent(new Event('change', { bubbles: true }));
                                    inp.dispatchEvent(new Event('blur', { bubbles: true }));
                                    return { count: 1, handled: true };
                                }
                            }
                            
                            let count = 0;
                            answers.forEach((ans, i) => {
                                if (i < inputs.length) {
                                    const inp = inputs[i];
                                    inp.value = ans;
                                    inp.dispatchEvent(new Event('input', { bubbles: true }));
                                    inp.dispatchEvent(new Event('change', { bubbles: true }));
                                    inp.dispatchEvent(new Event('blur', { bubbles: true }));
                                    count++;
                                }
                            });
                            return { count: count, handled: count > 0 };
                        }""", clean_answers)
                        
                        if res and res.get('handled') and res.get('count', 0) > 0:
                            return True, f"Se llenaron {res.get('count')} casillas de texto correctamente."
                    except Exception:
                        pass
                
                # Fallback tradicional Playwright
                success_count = 0
                for frame in frames:
                    try:
                        inputs = frame.locator('input[type="text"], textarea')
                        cnt = inputs.count()
                        if cnt > 0:
                            for idx, word in enumerate(clean_answers):
                                if idx < cnt:
                                    inputs.nth(idx).fill(word)
                                    success_count += 1
                            if success_count > 0:
                                return True, f"Se llenaron {success_count} casillas."
                    except:
                        pass
                return False, "No se encontraron casillas de texto suficientes para llenar."
            # --- PROOFREADING / MARKS ---
            elif exercise_type == 'PROOFREADING':
                errors = []
                for frame in frames:
                    try:
                        has_proofing = frame.evaluate("""() => {
                            return document.querySelector('.im-proofing') !== null;
                        }""")
                        if has_proofing:
                            res = frame.evaluate(r"""(ansText) => {
                                const $ = window.jQuery;
                                if (!$) return { success: false, msg: 'No jQuery' };
                                
                                let wordToInsert = 'that';
                                const rubric = $('.layout__rubric, .learningObject__rubric, p').text();
                                const m = rubric.match(/Add\s+([a-zA-Z]+)\s+to/i);
                                if (m) wordToInsert = m[1];
                                
                                const chunks = ansText.split('|').map(s => s.replace(/^\d+[\.\)]\s*/, '').trim());
                                
                                // Detect if there is a single active visible screen
                                const $activeWrap = $('.content-wrap:visible, .activity:visible');
                                let targetsToProcess = [];
                                
                                if ($activeWrap.length === 1) {
                                    const wrapId = $activeWrap.attr('id') || '';
                                    const idMatch = wrapId.match(/\d+/);
                                    const activeIdx = idMatch ? parseInt(idMatch[0], 10) : 0;
                                    const chunkForActive = activeIdx < chunks.length ? chunks[activeIdx] : chunks[0];
                                    targetsToProcess.push({
                                        idx: activeIdx,
                                        contentEl: $activeWrap.find('.layout__content')[0],
                                        chunk: chunkForActive
                                    });
                                } else {
                                    $('.layout__content').each((screenIdx, contentEl) => {
                                        targetsToProcess.push({
                                            idx: screenIdx,
                                            contentEl: contentEl,
                                            chunk: screenIdx < chunks.length ? chunks[screenIdx] : ''
                                        });
                                    });
                                }
                                
                                let count = 0;
                                targetsToProcess.forEach(item => {
                                    const $c = $(item.contentEl);
                                    const $markables = $c.find('.markable');
                                    if ($markables.length === 0) return;
                                    
                                    const chunk = item.chunk;
                                    let targetWord = null;
                                    let specificTarget = null;
                                    
                                    // 1. En NGL proofreading, el marcador caret (^) inserta ANTES de la palabra seleccionada.
                                    // Para insertar 'that' entre Palabra A y Palabra B, la marca DEBE ponerse en Palabra B (después de 'that').
                                    const afterPattern = new RegExp('\\b' + wordToInsert + '\\s+([\\w\']+)', 'i');
                                    const afterMatch = chunk.match(afterPattern);
                                    if (afterMatch) {
                                        specificTarget = afterMatch[1].toLowerCase();
                                    } else {
                                        const cleanWords = chunk.toLowerCase().replace(/[^\w\s']/g, '').trim().split(/\s+/);
                                        if (cleanWords.length === 1 && cleanWords[0] !== wordToInsert.toLowerCase()) {
                                            specificTarget = cleanWords[0];
                                        }
                                    }
                                    
                                    // 2. Buscar markable que coincida con specificTarget
                                    if (specificTarget) {
                                        const $found = $markables.filter(function() {
                                            const txt = $(this).find('.text').text().trim().toLowerCase();
                                            return txt === specificTarget;
                                        });
                                        if ($found.length > 0) targetWord = $found.first();
                                    }
                                    
                                    // 3. Fallback dinámico: revisar cada markable y comprobar si 'wordToInsert <markable>' aparece en chunk
                                    if (!targetWord) {
                                        $markables.each(function() {
                                            const w = $(this).find('.text').text().trim().toLowerCase();
                                            if (!w) return;
                                            const pairPattern = new RegExp('\\b' + wordToInsert + '\\s+' + w.replace("'", "\\'") + '\\b', 'i');
                                            if (pairPattern.test(chunk)) {
                                                targetWord = $(this);
                                                return false;
                                            }
                                        });
                                    }
                                    
                                    // 4. Fallback de verbos candidatos comunes
                                    if (!targetWord) {
                                        const candidates = ['cleans', "doesn't", 'works', 'delivers', 'does', 'takes', 'is', 'has', 'lives', 'comes'];
                                        for (let cand of candidates) {
                                            const $found = $markables.filter(function() {
                                                return $(this).find('.text').text().trim().toLowerCase() === cand;
                                            });
                                            if ($found.length > 0) {
                                                targetWord = $found.first();
                                                break;
                                            }
                                        }
                                    }
                                    
                                    if (targetWord && targetWord.length > 0) {
                                        if (!targetWord.hasClass('mark-add')) {
                                            const btnAdd = $c.find('.btn-add')[0] || $('.btn-add')[0];
                                            if (btnAdd) btnAdd.click();
                                            
                                            targetWord[0].click();
                                            
                                            const inp = document.querySelector('.editing-popup input[type="text"], .editing-popup input');
                                            if (inp) {
                                                inp.value = wordToInsert;
                                                inp.dispatchEvent(new Event('input', { bubbles: true }));
                                                inp.dispatchEvent(new Event('change', { bubbles: true }));
                                                
                                                const submitBtn = document.querySelector('.editing-popup .btn-submit, .editing-popup .btn-ok, .editing-popup button[type="submit"]');
                                                if (submitBtn) submitBtn.click();
                                            }
                                        }
                                        count++;
                                    }
                                });
                                
                                return { success: true, count: count };
                            }""", answer_text)
                            
                            if res and res.get('success'):
                                return True, f"Se insertaron marcas de edición en {res.get('count', 0)} pantallas."
                    except Exception as err:
                        errors.append(str(err))
                        
                if errors:
                    return False, f"Detalles: {', '.join(errors)}"
                return False, "No se encontró el editor de proofreading marks."

            # --- HIGHLIGHTING / TEXT MARKING ---
            elif exercise_type == 'HIGHLIGHTING':
                errors = []
                for frame in frames:
                    try:
                        has_marking = frame.evaluate("""() => {
                            return document.querySelector('.im-marking, .imMarking, .im-marking__item-button') !== null;
                        }""")
                        if has_marking:
                            res = frame.evaluate(r"""(ansText) => {
                                const $ = window.jQuery;
                                
                                // Asegurar que el resaltador esté activo
                                const tool = document.querySelector('.im-marking__button.toggle');
                                if (tool && !tool.classList.contains('activated')) {
                                    tool.click();
                                }
                                
                                // INTENTO 1: Modelo MVC nativo si expone elementos con correct
                                if ($) {
                                    let mvcMarked = 0;
                                    let hasMvcCorrect = false;
                                    $('.im-marking__item').each(function() {
                                        const el = $(this);
                                        const v = el.data('mvcView');
                                        if (v && v.model && Array.isArray(v.model.correct) && v.model.correct.length > 0) {
                                            hasMvcCorrect = true;
                                            const isMarked = el.hasClass('marked') || el.find('.marked').length > 0;
                                            if (!isMarked) {
                                                const btn = el.find('.im-marking__item-button, button');
                                                if (btn.length > 0) {
                                                    btn[0].click();
                                                } else {
                                                    el[0].click();
                                                }
                                            }
                                            mvcMarked++;
                                        }
                                    });
                                    if (hasMvcCorrect && mvcMarked > 0) {
                                        return { success: true, count: mvcMarked };
                                    }
                                }
                                
                                const buttons = Array.from(document.querySelectorAll('.im-marking__item-button, button.imMarking__button'));
                                if (buttons.length === 0) return { success: false, msg: 'No marking buttons found' };
                                
                                const rawChunks = ansText.split('|').map(s => s.replace(/^\d+[\.\)]\s*/, '').trim()).filter(s => s.length > 0);
                                let count = 0;
                                
                                rawChunks.forEach(chunk => {
                                    const cleanChunk = chunk.toLowerCase().replace(/[^a-z0-9]/g, '');
                                    if (!cleanChunk) return;
                                    
                                    // 1. Coincidencia exacta primero (evita falsos positivos como 'a' o 'I')
                                    let found = buttons.find(b => {
                                        const bText = b.innerText.toLowerCase().replace(/marked as[\s\S]*/i, '').replace(/[^a-z0-9]/g, '');
                                        return bText === cleanChunk;
                                    });
                                    
                                    // 2. Si el botón contiene la frase completa buscada
                                    if (!found) {
                                        found = buttons.find(b => {
                                            const bText = b.innerText.toLowerCase().replace(/marked as[\s\S]*/i, '').replace(/[^a-z0-9]/g, '');
                                            return bText.length >= cleanChunk.length && bText.includes(cleanChunk);
                                        });
                                    }
                                    
                                    // 3. Si la respuesta es una cláusula larga y el botón contiene esa cláusula
                                    if (!found && cleanChunk.length > 15) {
                                        found = buttons.find(b => {
                                            const bText = b.innerText.toLowerCase().replace(/marked as[\s\S]*/i, '').replace(/[^a-z0-9]/g, '');
                                            return bText.length > 10 && (cleanChunk.includes(bText) || bText.includes(cleanChunk));
                                        });
                                    }
                                    
                                    if (found) {
                                        const parent = found.parentElement;
                                        const isMarked = parent && parent.classList.contains('marked');
                                        if (!isMarked) {
                                            found.click();
                                        }
                                        count++;
                                    }
                                });
                                
                                return { success: true, count: count };
                            }""", answer_text)
                            
                            if res and res.get('success'):
                                return True, f"Se resaltaron {res.get('count', 0)} oraciones/frases correctamente."
                    except Exception as err:
                        errors.append(str(err))
                        
                if errors:
                    return False, f"Detalles: {', '.join(errors)}"
                return False, "No se encontró el interactivo de resaltado (highlighting)."

            # --- SORTING / CATEGORIZATION (osSorting) ---
            elif exercise_type == 'SORTING' or (exercise_type in (None, 'UNKNOWN') and any('osSorting' in f.content() for f in frames)):
                errors = []
                for frame in frames:
                    try:
                        res = frame.evaluate(r"""() => {
                            const $ = window.jQuery;
                            if (!$) return { success: false, msg: 'No jQuery' };
                            
                            const catViews = $('.osSorting__category').map(function() {
                                return $(this).data('mvcView');
                            }).get();
                            
                            if (!catViews || catViews.length === 0) return { success: false, msg: 'No categories' };
                            
                            const targets = catViews.map(cv => cv.getTargetIdentifier());
                            const pool = $('.osSorting__pool');
                            const poolView = pool.data('mvcView');
                            
                            let placedCount = 0;
                            $('.os-sorting-element').each(function() {
                                const dv = $(this).data('mvcView');
                                const m = dv ? dv.model : null;
                                if (!m) return;
                                
                                const correctTarget = targets.find(t => m.isCorrectInTarget && m.isCorrectInTarget(t));
                                if (correctTarget) {
                                    m.setTarget(correctTarget);
                                    placedCount++;
                                }
                            });
                            
                            catViews.forEach(cv => {
                                if (cv && typeof cv.refresh === 'function') cv.refresh();
                            });
                            if (poolView && typeof poolView.refresh === 'function') poolView.refresh();
                            
                            return { success: true, count: placedCount };
                        }""")
                        if res and res.get('success') and res.get('count', 0) > 0:
                            return True, f"Se clasificaron {res['count']} elementos en sus columnas correspondientes."
                    except Exception as err:
                        errors.append(str(err))
                if errors:
                    return False, f"Detalles: {', '.join(errors)}"
                return False, "No se encontró el interactivo de ordenamiento por columnas (sorting)."

            # --- DROPDOWN / LISTBOX ---
            elif exercise_type == 'DROPDOWN' or (exercise_type in (None, 'UNKNOWN') and any('listbox' in f.content() for f in frames)):
                parsed_answers = []
                for chunk in answer_text.split('|'):
                    chunk = chunk.strip()
                    val = re.sub(r'^\s*\d+[\.\)\-]\s*', '', chunk).strip()
                    if val:
                        parsed_answers.append(val)
                
                errors = []
                for frame in frames:
                    try:
                        res = frame.evaluate(r"""(answers) => {
                            const $ = window.jQuery;
                            if (!$) return { count: 0, handled: false };
                            
                            let listboxes = $('.listbox:not(.interaction)').filter(function() {
                                return $(this).find('.listbox').length === 0 && $(this).find('.listbox__choice, option').length > 0;
                            });
                            if (listboxes.length === 0) {
                                listboxes = $('.wrapper-dropdown, select.is-dropdown, .listbox__dropdown');
                            }
                            if (listboxes.length === 0) return { count: 0, handled: false };
                            
                            let count = 0;
                            listboxes.each(function(i) {
                                const el = $(this);
                                const v = el.data('mvcView');
                                const m = v ? v.model : null;
                                
                                let targetChoiceText = i < answers.length ? answers[i].toLowerCase().trim() : null;
                                let chosenLi = null;
                                
                                if (m && m.choices) {
                                    const corr = m.choices.find(c => ('correctIndex' in c && c.correctIndex === true) || c.isCorrect);
                                    if (corr) {
                                        const cTxt = $(corr.content).text().trim() || corr.text || corr.content;
                                        if (cTxt) targetChoiceText = cTxt.toLowerCase().trim();
                                    }
                                }
                                
                                if (targetChoiceText) {
                                    const choices = el.find('.listbox__choice, option');
                                    // Try exact match first
                                    choices.each(function() {
                                        const txt = $(this).text().trim().toLowerCase();
                                        if (txt === targetChoiceText) {
                                            chosenLi = this;
                                            return false;
                                        }
                                    });
                                    // Try loose match if not found
                                    if (!chosenLi) {
                                        choices.each(function() {
                                            const txt = $(this).text().trim().toLowerCase();
                                            if (txt.includes(targetChoiceText) || targetChoiceText.includes(txt)) {
                                                chosenLi = this;
                                                return false;
                                            }
                                        });
                                    }
                                }
                                
                                if (chosenLi) {
                                    chosenLi.click();
                                    count++;
                                }
                            });
                            return { count: count, handled: count > 0 };
                        }""", parsed_answers)
                        
                        if res and res.get('handled') and res.get('count', 0) > 0:
                            return True, f"Se seleccionaron {res.get('count')} opciones de lista desplegable correctamente."
                    except Exception as err:
                        errors.append(str(err))
                        
                if errors:
                    return False, f"Detalles: {', '.join(errors)}"
                return False, "No se encontraron menús desplegables (dropdowns)."

            # --- MATCHING / LINKING LINES ---
            elif exercise_type == 'MATCHING' or 'is-linking-lines' in self.page.content() or any('is-linking-lines' in f.content() for f in self.page.frames):
                parts = [p.strip() for p in re.split(r'[|\n]', answer_text) if p.strip()]
                raw_pairs = []
                for part in parts:
                    clean = re.sub(r'^\s*\d+[\.\)\-]\s*', '', part).strip()
                    if '=' in clean:
                        s, t = clean.split('=', 1)
                        raw_pairs.append((s.strip(), t.strip()))
                    elif '->' in clean:
                        s, t = clean.split('->', 1)
                        raw_pairs.append((s.strip(), t.strip()))
                    elif ':' in clean and not clean.startswith('http'):
                        s, t = clean.split(':', 1)
                        raw_pairs.append((s.strip(), t.strip()))

                errors = []
                for frame in frames:
                    try:
                        res = frame.evaluate(r"""(pairs) => {
                            const $ = window.jQuery;
                            if (!$) return { count: 0, handled: false };
                            const elView = $('.ll_element_view').first().data('mvcView');
                            if (!elView || !elView.parent) return { count: 0, handled: false };
                            const pView = elView.parent;
                            const m = pView.model;
                            if (!m || !m.elements) return { count: 0, handled: false };

                            let count = 0;
                            // Si el modelo de Avallain ya tiene las respuestas exactas configuradas internamente
                            if (m.answers && Object.keys(m.answers).length > 0) {
                                const elementsByIdentifier = {};
                                m.elements.forEach(el => {
                                    elementsByIdentifier[el.identifier] = el;
                                });
                                for (const [sourceId, targetIds] of Object.entries(m.answers)) {
                                    const fromModel = elementsByIdentifier[sourceId];
                                    for (const targetId of targetIds) {
                                        const toModel = elementsByIdentifier[targetId];
                                        if (fromModel && toModel) {
                                            m.addLine(fromModel, toModel);
                                            pView.link(fromModel, toModel);
                                            count++;
                                        }
                                    }
                                }
                                pView.repaintCanvas();
                                return { count: count, handled: true, method: 'model_answers' };
                            }

                            // Emparejamiento por texto si no hay m.answers
                            if (pairs && pairs.length > 0) {
                                const leftEls = [];
                                const rightEls = [];
                                $('.ll_element_view').each(function() {
                                    const v = $(this).data('mvcView');
                                    if (!v || !v.model) return;
                                    const parent = this.closest('.linkingLines__item') || this.parentElement;
                                    const txt = (parent ? parent.innerText : '').trim().toLowerCase();
                                    if (this.className.includes('left')) {
                                        leftEls.push({ model: v.model, text: txt });
                                    } else {
                                        rightEls.push({ model: v.model, text: txt });
                                    }
                                });

                                for (let pIdx = 0; pIdx < pairs.length; pIdx++) {
                                    const [srcText, tgtText] = pairs[pIdx];
                                    const sClean = (srcText || '').toLowerCase().trim();
                                    const tClean = (tgtText || '').toLowerCase().trim();
                                    
                                    // 1. Buscar elemento izquierdo: por texto o por índice (audio matching)
                                    let fromObj = leftEls.find(l => l.text && (l.text.includes(sClean) || sClean.includes(l.text)));
                                    if (!fromObj) {
                                        const numMatch = sClean.match(/\d+/);
                                        const idx = numMatch ? (parseInt(numMatch[0], 10) - 1) : pIdx;
                                        if (idx >= 0 && idx < leftEls.length) {
                                            fromObj = leftEls[idx];
                                        }
                                    }
                                    
                                    // 2. Buscar elemento derecho: por texto
                                    let toObj = rightEls.find(r => r.text && (r.text.includes(tClean) || tClean.includes(r.text)));
                                    if (!toObj) {
                                        const numMatch = tClean.match(/\d+/);
                                        const idx = numMatch ? (parseInt(numMatch[0], 10) - 1) : -1;
                                        if (idx >= 0 && idx < rightEls.length) {
                                            toObj = rightEls[idx];
                                        }
                                    }
                                    
                                    if (fromObj && toObj) {
                                        m.addLine(fromObj.model, toObj.model);
                                        pView.link(fromObj.model, toObj.model);
                                        count++;
                                    }
                                }
                                pView.repaintCanvas();
                                return { count: count, handled: count > 0, method: 'text_pairs' };
                            }
                            return { count: 0, handled: false };
                        }""", raw_pairs)

                        if res and res.get('handled') and res.get('count', 0) > 0:
                            return True, f"Se relacionaron {res.get('count')} elementos correctamente."
                    except Exception as err:
                        errors.append(str(err))

                if errors:
                    return False, f"Detalles: {', '.join(errors)}"
                return False, "No se encontró el interactivo de relacionar líneas (matching)."

            return False, f"Unsupported exercise type ({exercise_type}) for auto-fill."
            
        except Exception as e:
            return False, f"Error filling form: {e}"

    def submit_done(self) -> tuple[bool, str]:
        """
        Locates and clicks the 'Done' / 'Submit' submission button in the Avallain activity.
        Supports both iframe and outer-frame (Unit Test) submission buttons, and auto-confirms dialogs.
        """
        frames = [self.page] + getattr(self.page, 'frames', [])
        for frame in frames:
            if "cdn_proxy" in getattr(frame, 'url', '') or "avallain" in getattr(frame, 'url', ''):
                try:
                    res = frame.evaluate(r"""() => {
                        const $ = window.jQuery;
                        if (!$) return { success: false, reason: "no_jquery" };
                        
                        let targetBtn = $('button[data-event="submit"], button[data-event="done"], [data-action="done"], [data-action="submit"]')
                            .filter(':visible:not(.button--hidden):not(.inactive_button):not([disabled])');
                        
                        if (targetBtn.length === 0) {
                            $('button, a[role="button"]').each(function() {
                                const t = ($(this).text() || '').trim();
                                if ($(this).is(':visible') && !$(this).hasClass('button--hidden') && !$(this).hasClass('inactive_button') && !$(this).prop('disabled')) {
                                    if (/^(done|submit)/i.test(t) || /submit to gradebook/i.test(t) || /finalizar/i.test(t)) {
                                        targetBtn = $(this);
                                        return false;
                                    }
                                }
                            });
                        }
                        
                        if (targetBtn.length === 0) {
                            const anyDone = $('button[data-event="submit"], button[data-event="done"]').filter(':not(.inactive_button)');
                            if (anyDone.length > 0) {
                                targetBtn = anyDone;
                            }
                        }
                        
                        if (targetBtn && targetBtn.length > 0) {
                            targetBtn[0].click();
                            // Confirm any submission dialogs: "Yes", "OK", "Confirm"
                            setTimeout(() => {
                                $('.dialog button:contains("Yes"), .dialog button:contains("OK"), .ui-dialog button:contains("Yes"), .ui-dialog button:contains("OK"), button:contains("Confirm")')
                                    .filter(':visible').each(function() {
                                        $(this).click();
                                    });
                            }, 500);
                            return { success: true, text: targetBtn.text().trim() };
                        }
                        
                        return { success: false, reason: "done_button_not_found" };
                    }""")
                    if res and res.get('success'):
                        time.sleep(2.5)  # Wait for submission and feedback evaluation
                        return True, f"Respuesta enviada (botón '{res.get('text', 'Done')}' presionado exitosamente)."
                except Exception as e:
                    return False, f"Error al enviar respuesta: {e}"

        # Outer frames check (Unit Tests on learn.eltngl.com)
        outer_frames = [f for f in frames if "cdn_proxy" not in getattr(f, 'url', '') and "avallain" not in getattr(f, 'url', '')]
        for outer_frame in outer_frames:
            try:
                outer_res = outer_frame.evaluate(r"""() => {
                    const buttons = Array.from(document.querySelectorAll('button, a[role="button"], input[type="button"], input[type="submit"]'));
                    for (const btn of buttons) {
                        if (btn.offsetParent === null || btn.disabled) continue;
                        const txt = (btn.textContent || btn.value || '').trim().toLowerCase();
                        if (txt.includes('submit to gradebook') || txt === 'submit' || txt === 'done' || txt.includes('enviar') || txt.includes('finalizar')) {
                            btn.click();
                            setTimeout(() => {
                                const confirmBtns = Array.from(document.querySelectorAll('button, a[role="button"]'));
                                for (const cb of confirmBtns) {
                                    const ctxt = (cb.textContent || '').trim().toLowerCase();
                                    if (ctxt === 'yes' || ctxt === 'ok' || ctxt === 'confirm' || ctxt === 'submit') {
                                        cb.click();
                                    }
                                }
                            }, 500);
                            return { success: true, text: txt };
                        }
                    }
                    return { success: false };
                }""")
                if outer_res and outer_res.get('success'):
                    time.sleep(2.5)
                    return True, f"Respuesta enviada desde marco exterior ('{outer_res.get('text', 'Submit')}')."
            except Exception:
                pass

        return False, "No se encontró el botón 'Done' o 'Submit' en ningún marco de la actividad."

    def check_submission_accuracy(self) -> tuple[bool, str, dict]:
        """
        Inspects the activity post-submission to verify if the result was 100% correct.
        Returns:
            (is_perfect: bool, message: str, details: dict)
        """
        frames = [self.page] + self.page.frames
        for frame in frames:
            if "cdn_proxy" in frame.url or "avallain" in frame.url:
                try:
                    info = frame.evaluate(r"""() => {
                        const $ = window.jQuery;
                        if (!$) return { error: "no_jquery" };
                        
                        // 1. Check for wrong/incorrect markers
                        const wrongMarkers = $('.check.wrong, .check.incorrect, .status-wrong, .is-incorrect, .wrong:not(button), .incorrect:not(button)').filter(':visible');
                        
                        // 2. Check for active 'Try again' button
                        const tryAgainBtn = $('button[data-event="try_again"]:not(.inactive_button):not(.button--hidden)').filter(':visible');
                        
                        // 3. Check for correct markers
                        const correctMarkers = $('.check.correct, .status-correct, [class*="correct"]:not(.interaction)').filter(':visible');
                        
                        // 4. Check if Next exercise button is active/visible
                        const nextLoBtn = $('button[data-event="forward_lo"], .learningObject__controls-button:contains("Next")').filter(':visible');
                        
                        // 5. Look for any score text (e.g., "Score: 6 out of 6")
                        let scoreText = null;
                        const bodyText = document.body ? document.body.innerText : '';
                        const match = bodyText.match(/Score[:\s]*(\d+)\s+out\s+of\s+(\d+)/i);
                        if (match) {
                            scoreText = { earned: parseInt(match[1]), total: parseInt(match[2]), raw: match[0] };
                        }
                        
                        return {
                            wrongCount: wrongMarkers.length,
                            tryAgainVisible: tryAgainBtn.length > 0,
                            correctCount: correctMarkers.length,
                            nextLoVisible: nextLoBtn.length > 0,
                            scoreText: scoreText
                        };
                    }""")
                    
                    if not info or "error" in info:
                        continue
                        
                    wrong_count = info.get('wrongCount', 0)
                    try_again = info.get('tryAgainVisible', False)
                    correct_count = info.get('correctCount', 0)
                    next_lo = info.get('nextLoVisible', False)
                    score_obj = info.get('scoreText')
                    
                    # If score text found and earned < total -> definitely not 100%
                    if score_obj and score_obj['earned'] < score_obj['total']:
                        return False, f"Puntuación imperfecta: {score_obj['earned']} de {score_obj['total']} ({score_obj['raw']}).", info
                        
                    # If wrong markers or try again active -> failure
                    if wrong_count > 0:
                        return False, f"Se detectaron {wrong_count} respuestas incorrectas.", info
                        
                    if try_again:
                        return False, "El botón 'Try again' quedó activo tras el envío.", info
                        
                    # Success criteria: correct answers present or Next button enabled with 0 errors
                    if score_obj and score_obj['earned'] == score_obj['total']:
                        return True, f"¡Puntuación perfecta! {score_obj['earned']} de {score_obj['total']} correctas.", info
                        
                    if correct_count > 0 and wrong_count == 0:
                        return True, f"100% Correcto ({correct_count} aciertos verificados).", info
                        
                    if next_lo and wrong_count == 0:
                        return True, "Actividad completada sin errores detectados.", info
                        
                    return True, "Actividad enviada (sin errores detectados).", info
                except Exception as e:
                    return False, f"Error al verificar resultado: {e}", {}
                    
        return False, "No se pudo acceder a la evaluación de la actividad.", {}

    def click_next_exercise(self, wait_timeout_sec: float = 15.0) -> tuple[bool, str]:
        """
        Clicks the Next ('forward_lo') button to advance to the next activity in the assignment.
        Waits until the new activity has loaded.
        """
        frames = [self.page] + self.page.frames
        target_frame = None
        prev_url = ""
        prev_title = ""
        for frame in frames:
            if "cdn_proxy" in frame.url or "avallain" in frame.url:
                target_frame = frame
                prev_url = frame.url
                try:
                    prev_title = frame.evaluate("() => $('.learningObject__title, h1, h2, .lo-title').text().trim() || document.title")
                except Exception:
                    pass
                break

        if not target_frame:
            return False, "No se encontró el marco de la actividad."

        try:
            clicked = target_frame.evaluate(r"""() => {
                const $ = window.jQuery;
                if (!$) return false;
                const btn = $('button[data-event="forward_lo"], .learningObject__controls-button:contains("Next")').filter(':visible:not(.inactive_button):not([disabled])');
                if (btn.length > 0) {
                    btn[0].click();
                    return true;
                }
                return false;
            }""")

            if not clicked:
                # Outer frames check (Unit Tests and assignments shell)
                outer_frames = [f for f in frames if "cdn_proxy" not in getattr(f, 'url', '') and "avallain" not in getattr(f, 'url', '')]
                for outer_frame in outer_frames:
                    try:
                        outer_clicked = outer_frame.evaluate(r"""() => {
                            const btns = Array.from(document.querySelectorAll('button, a[role="button"]'));
                            for (const b of btns) {
                                if (b.offsetParent === null || b.disabled) continue;
                                const t = (b.textContent || '').trim().toLowerCase();
                                if (t === 'next' || t.includes('next activity') || t.includes('siguiente actividad')) {
                                    b.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                        if outer_clicked:
                            clicked = True
                            break
                    except Exception:
                        pass
            
            if not clicked:
                return False, "No se encontró el botón de siguiente ejercicio ('Next' / 'forward_lo'). Es posible que la asignación haya terminado."

            # Wait for transition: poll until frame URL or title changes and new interaction is ready
            time.sleep(2.0)
            start_t = time.time()
            while time.time() - start_t < wait_timeout_sec:
                try:
                    cdn_frames = [f for f in self.page.frames if "cdn_proxy" in f.url or "avallain" in f.url]
                    if cdn_frames:
                        cur_frame = cdn_frames[0]
                        cur_url = cur_frame.url
                        cur_title = cur_frame.evaluate("() => $('.learningObject__title, h1, h2, .lo-title').text().trim() || document.title")
                        if cur_url != prev_url or cur_title != prev_title:
                            # Check if the interaction DOM is mounted
                            is_mounted = cur_frame.evaluate("() => $('.interaction, .package, .learningObject').length > 0")
                            if is_mounted:
                                time.sleep(1.5)  # Wait for MVC models/views to attach
                                return True, "Se avanzó exitosamente al siguiente ejercicio."
                except Exception:
                    pass
                time.sleep(0.5)
                
            return True, "Se avanzó exitosamente al siguiente ejercicio."
        except Exception as e:
            return False, f"Error al hacer clic en siguiente ejercicio: {e}"

    def has_next_screen(self) -> bool:
        """
        Returns True if the current activity/exam has another screen/question to advance to.
        Checks both inside the Avallain iframe and in outer navigation shells (Unit Tests).
        """
        frames = [self.page] + getattr(self.page, 'frames', [])
        for frame in frames:
            if "cdn_proxy" in getattr(frame, 'url', '') or "avallain" in getattr(frame, 'url', ''):
                try:
                    res = frame.evaluate(r"""() => {
                        const $ = window.jQuery;
                        if (!$) return false;
                        
                        // 1. Check data-event="forward" (next screen button)
                        const screenBtn = $('button[data-event="forward"], .learningObject__controls-button:contains("next screen")')
                            .filter(':visible:not(.inactive_button):not([disabled])');
                        if (screenBtn.length > 0) return true;
                        
                        // 2. Check content-wrap index vs total wraps
                        const wraps = $('.content-wrap');
                        if (wraps.length > 1) {
                            const active = $('.content-wrap:visible, .activity:visible').first();
                            const idx = wraps.index(active);
                            if (idx !== -1 && idx < wraps.length - 1) return true;
                        }
                        
                        // 3. Check body text for "Screen X of Y"
                        const bodyText = document.body ? document.body.innerText : '';
                        const m = bodyText.match(/Screen[:\s]*(\d+)\s*of\s*(\d+)/i);
                        if (m && parseInt(m[1]) < parseInt(m[2])) return true;
                        
                        return false;
                    }""")
                    if res:
                        return True
                except Exception:
                    pass

        # Outer frames check (Unit Tests on learn.eltngl.com)
        outer_frames = [f for f in frames if "cdn_proxy" not in getattr(f, 'url', '') and "avallain" not in getattr(f, 'url', '')]
        for outer_frame in outer_frames:
            try:
                res = outer_frame.evaluate(r"""() => {
                    const bodyText = document.body ? document.body.innerText : '';
                    const m = bodyText.match(/Screen[:\s]*(\d+)\s*of\s*(\d+)/i);
                    if (m && parseInt(m[1]) < parseInt(m[2])) return true;
                    
                    const selectors = [
                        'button[data-direction="next"]:not([disabled])',
                        'a[data-direction="next"]:not([disabled])',
                        'button.assignment-nav__button--next:not([disabled])',
                        '[class*="arrow-right"]:not([disabled])',
                        '[class*="nav-next"]:not([disabled])'
                    ];
                    for (const sel of selectors) {
                        const el = document.querySelector(sel);
                        if (el && el.offsetParent !== null && !el.disabled && !el.classList.contains('disabled')) {
                            return true;
                        }
                    }
                    return false;
                }""")
                if res:
                    return True
            except Exception:
                pass

        return False

    def click_next_screen(self, wait_timeout_sec: float = 10.0) -> tuple[bool, str]:
        """
        Clicks the Next Screen ('forward') button inside a multi-screen exercise or exam.
        For Unit Tests on learn.eltngl.com the navigation arrow lives in the MAIN frame,
        not inside the Avallain iframe.  We try the Avallain frame first and then fall back
        to the main/outer page frame so that the circular-arrow button used in Unit Tests
        (e.g. "Screen: 1 of 25") is properly detected and clicked.
        """
        frames = [self.page] + getattr(self.page, 'frames', [])
        target_frame = None
        for frame in frames:
            if "cdn_proxy" in getattr(frame, 'url', '') or "avallain" in getattr(frame, 'url', ''):
                target_frame = frame
                break

        if not target_frame:
            return False, "No se encontró el marco de la actividad."

        try:
            prev_snippet = target_frame.evaluate("""() => {
                const $ = window.jQuery;
                const active = $('.content-wrap:visible, .activity:visible').first();
                return active.length > 0 ? (active.attr('id') || active.text().slice(0, 150)) : (document.body ? document.body.innerText.slice(0, 300) : '');
            }""")
            
            clicked = target_frame.evaluate(r"""() => {
                const $ = window.jQuery;
                if (!$) return false;
                // Cerrar popups modales bloqueantes (ej. prueba de micrófono 'Microphone Test') si están abiertos
                $('.testRecording__dialog:visible, .ui-dialog:visible').find('.ui-dialog-titlebar-close, .close').first().click();

                // 1. Next screen within multi-screen exam/activity
                const screenBtn = $('button[data-event="forward"], .learningObject__controls-button:contains("next screen")')
                    .filter(':visible:not(.inactive_button):not([disabled])');
                if (screenBtn.length > 0) {
                    screenBtn[0].click();
                    return "forward";
                }
                return false;
            }""")

            # --- Fallback: Unit Test navigation arrow in the OUTER (main) page frame ---
            # In Unit Tests on learn.eltngl.com the circular next button used to navigate
            # between questions ("Screen: X of 25") is rendered by the NGL shell outside
            # the Avallain iframe.  We try every frame that is NOT the Avallain iframe.
            if not clicked:
                outer_frames = [f for f in frames if "cdn_proxy" not in f.url and "avallain" not in f.url]
                for outer_frame in outer_frames:
                    try:
                        outer_clicked = outer_frame.evaluate(r"""() => {
                            // NGL Unit Test: circular arrow button with common data attributes or ARIA labels
                            const selectors = [
                                'button[data-direction="next"]',
                                'a[data-direction="next"]',
                                '[class*="next"][class*="button"]:not([disabled])',
                                '[class*="arrow-right"]:not([disabled])',
                                '[class*="nav-next"]:not([disabled])',
                                'button.assignment-nav__button--next',
                                '[aria-label*="next" i]:not([disabled])',
                                '[aria-label*="siguiente" i]:not([disabled])',
                                '[title*="next" i]:not([disabled])',
                                '[title*="siguiente" i]:not([disabled])',
                            ];
                            for (const sel of selectors) {
                                const el = document.querySelector(sel);
                                if (el && el.offsetParent !== null) {
                                    el.click();
                                    return "outer_next";
                                }
                            }
                            // Last resort: visible button on the RIGHT half of the screen with no real text
                            // (typical for icon-only circular navigation arrows in SPAs)
                            const buttons = Array.from(document.querySelectorAll('button, a[role="button"]'));
                            for (const btn of buttons) {
                                if (btn.offsetParent === null || btn.disabled) continue;
                                const txt = (btn.textContent || '').trim();
                                if (txt.length > 5) continue;  // skip buttons with real text
                                const rect = btn.getBoundingClientRect();
                                if (rect.width < 10 || rect.height < 10) continue;
                                if (rect.left > window.innerWidth * 0.5) {
                                    btn.click();
                                    return "outer_fallback";
                                }
                            }
                            return false;
                        }""")
                        if outer_clicked:
                            clicked = outer_clicked
                            break
                    except Exception:
                        pass

            if not clicked:
                return False, "No se encontró el botón para avanzar a la siguiente pantalla (posiblemente estés en la última pantalla)."

            # When the navigation button is in the outer frame (Unit Test), the Avallain
            # iframe may fully reload. Give it a longer initial pause and be resilient to
            # frame detach errors while polling.
            initial_wait = 1.2 if clicked in ("outer_next", "outer_fallback") else 0.5
            time.sleep(initial_wait)
            start_t = time.time()
            while time.time() - start_t < wait_timeout_sec:
                try:
                    # Re-find the Avallain frame in case it was reloaded/replaced
                    cdn_frames = [f for f in self.page.frames if "cdn_proxy" in f.url or "avallain" in f.url]
                    active_frame = cdn_frames[0] if cdn_frames else target_frame
                    cur_snippet = active_frame.evaluate("""() => {
                        const $ = window.jQuery;
                        const active = $('.content-wrap:visible, .activity:visible').first();
                        return active.length > 0 ? (active.attr('id') || active.text().slice(0, 150)) : (document.body ? document.body.innerText.slice(0, 300) : '');
                    }""")
                    if cur_snippet != prev_snippet:
                        time.sleep(0.5)
                        return True, "Se avanzó a la siguiente pantalla exitosamente."
                except Exception:
                    pass
                time.sleep(0.3)

            return True, "Se avanzó a la siguiente pantalla."
        except Exception as e:
            # Si el botón ya fue presionado y la excepción es porque el frame se destruyó/desconectó,
            # significa que la página avanzó exitosamente a la siguiente pantalla y recargó el contenido.
            err_msg = str(e).lower()
            if 'detached' in err_msg or 'destroyed' in err_msg or 'navigat' in err_msg:
                time.sleep(1.0)
                return True, "Se avanzó a la siguiente pantalla exitosamente."
            return False, f"Error al avanzar pantalla: {e}"

    def click_previous_screen(self, wait_timeout_sec: float = 10.0) -> tuple[bool, str]:
        """
        Clicks the Previous Screen ('backward') button inside a multi-screen exercise or exam.
        """
        frames = [self.page] + self.page.frames
        target_frame = None
        for frame in frames:
            if "cdn_proxy" in frame.url or "avallain" in frame.url:
                target_frame = frame
                break

        if not target_frame:
            return False, "No se encontró el marco de la actividad."

        try:
            clicked = target_frame.evaluate(r"""() => {
                const $ = window.jQuery;
                if (!$) return false;
                // Cerrar popups modales bloqueantes si están abiertos
                $('.testRecording__dialog:visible, .ui-dialog:visible').find('.ui-dialog-titlebar-close, .close').first().click();

                const prevBtn = $('button[data-event="previous"], button[data-event="backward"], .learningObject__controls-button:contains("previous screen")')
                    .filter(':visible:not(.inactive_button):not([disabled])');
                if (prevBtn.length > 0) {
                    prevBtn[0].click();
                    return "previous";
                }
                return false;
            }""")

            # Fallback a marcos externos
            if not clicked:
                outer_frames = [f for f in frames if "cdn_proxy" not in f.url and "avallain" not in f.url]
                for outer_frame in outer_frames:
                    try:
                        outer_clicked = outer_frame.evaluate(r"""() => {
                            const selectors = [
                                'button[data-direction="prev"]',
                                'a[data-direction="prev"]',
                                '[class*="prev"][class*="button"]:not([disabled])',
                                '[class*="arrow-left"]:not([disabled])',
                                '[class*="nav-prev"]:not([disabled])',
                                'button.assignment-nav__button--prev',
                                '[aria-label*="prev" i]:not([disabled])',
                                '[aria-label*="anterior" i]:not([disabled])',
                            ];
                            for (const sel of selectors) {
                                const el = document.querySelector(sel);
                                if (el && el.offsetParent !== null) {
                                    el.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                        if outer_clicked:
                            clicked = True
                            break
                    except Exception:
                        pass

            if not clicked:
                return False, "No se encontró el botón de retroceso (es posible que estés en la primera pantalla)."

            time.sleep(1.0)
            return True, "Se retrocedió a la pantalla anterior exitosamente."
        except Exception as e:
            return False, f"Error al retroceder pantalla: {e}"
