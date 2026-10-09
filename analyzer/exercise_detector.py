from enum import Enum

class ExerciseType(Enum):
    SPEAKING = "SPEAKING"
    DRAG_AND_DROP = "DRAG_AND_DROP"
    REORDERING = "REORDERING"
    SORTING = "SORTING"
    DROPDOWN = "DROPDOWN"
    MATCHING = "MATCHING"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    PROOFREADING = "PROOFREADING"
    HIGHLIGHTING = "HIGHLIGHTING"
    FILL_BLANK = "FILL_BLANK"
    LISTENING = "LISTENING"
    PRESENTATION = "PRESENTATION"
    UNKNOWN = "UNKNOWN"

class ExerciseDetector:
    def __init__(self, page):
        self.page = page

    def detect_type(self) -> ExerciseType:
        if not self.page:
            return ExerciseType.UNKNOWN
            
        try:
            if hasattr(self.page, 'main_frame'):
                frames = [self.page.main_frame] + getattr(self.page, 'frames', [])
            else:
                frames = [self.page]
            found_types = set()
            
            for frame in frames:
                try:
                    res = frame.evaluate(r"""() => {
                        const $ = window.jQuery;
                            let activeWrap = $('.content-wrap:visible, .activity:visible').first();
                            if (activeWrap.length === 0) {
                                activeWrap = $('.content-wrap, .activity').filter(function() { return $(this).css('display') !== 'none'; }).first();
                            }
                            const $scope = activeWrap.length > 0 ? activeWrap : $(document.body);
                            const has = (sel) => $scope.find(sel).length > 0;
                            const rubricText = $scope.find('.layout__rubric, .rubric, .learningObject__rubric').text().toLowerCase();

                            return {
                                speaking: has('.contentblock--SpeakingAndRecording, .voice-recording, .is-radiobutton-voice') || (rubricText.includes('speak') && has('.playbutton, audio, .record')),
                                sorting: has('.osSorting__category, .os-sorting-element, .osSorting'),
                                reordering: has('.shuffle_interaction, .os-sequence__shuffle, .os-sequence-element, .ui-sortable'),
                                matching: has('.is-linking-lines, .ll_element_view, .isLinkingMultipleLines__handle, .matching_interaction, [class*="linking-lines"]'),
                                highlighting: has('.im-marking, .imMarking, .im-marking__item-button, button.imMarking__button'),
                                proofing: has('.im-proofing, .im-proofing__editor, .markable, .btn-add'),
                                dragdrop: has('.om-text-gap__droppable, .drag_holder'),
                                dropdown: has('.is-dropdown, .listbox, .rich-dropdown, .wrapper-dropdown'),
                                multichoice: has('input[type="radio"], .radio-group, .choice_interaction, .is-radiobutton-choice'),
                                fillblank: has('input.textGapItem__input, .textgap input, input[type="text"], textarea'),
                                listening: has('audio, .audio-player, .playbutton, [data-playable-media]'),
                                presentation: has('.pp-present, [class*="pp-present"], .presentation, .is-presentation')
                            };
                        }

                        // Fallback Vanilla JS
                        const hasVis = (sel) => {
                            const nodes = document.querySelectorAll(sel);
                            for (let i = 0; i < nodes.length; i++) {
                                const n = nodes[i];
                                if (n.offsetParent !== null && !n.closest('.activity--hidden, .screen--hidden, .hidden')) {
                                    return true;
                                }
                            }
                            return false;
                        };

                        return {
                            speaking: hasVis('.contentblock--SpeakingAndRecording, .voice-recording, .is-radiobutton-voice'),
                            sorting: hasVis('.osSorting__category, .os-sorting-element, .osSorting'),
                            reordering: hasVis('.shuffle_interaction, .os-sequence__shuffle, .os-sequence-element, .ui-sortable'),
                            matching: hasVis('.is-linking-lines, .ll_element_view, .isLinkingMultipleLines__handle, .matching_interaction'),
                            highlighting: hasVis('.im-marking, .imMarking, .im-marking__item-button'),
                            proofing: hasVis('.im-proofing, .im-proofing__editor, .markable'),
                            dragdrop: hasVis('.om-text-gap__droppable, .drag_holder'),
                            dropdown: hasVis('.is-dropdown, .listbox, .wrapper-dropdown'),
                            multichoice: hasVis('input[type="radio"], .radio-group, .choice_interaction'),
                            fillblank: hasVis('input.textGapItem__input, .textgap input, input[type="text"], textarea'),
                            listening: hasVis('audio, .audio-player, .playbutton'),
                            presentation: hasVis('.pp-present, .presentation')
                        };
                    }""")
                    
                    if res:
                        if res.get('speaking'): found_types.add(ExerciseType.SPEAKING)
                        if res.get('sorting'): found_types.add(ExerciseType.SORTING)
                        if res.get('reordering'): found_types.add(ExerciseType.REORDERING)
                        if res.get('matching'): found_types.add(ExerciseType.MATCHING)
                        if res.get('highlighting'): found_types.add(ExerciseType.HIGHLIGHTING)
                        if res.get('proofing'): found_types.add(ExerciseType.PROOFREADING)
                        if res.get('dragdrop'): found_types.add(ExerciseType.DRAG_AND_DROP)
                        if res.get('dropdown'): found_types.add(ExerciseType.DROPDOWN)
                        if res.get('multichoice'): found_types.add(ExerciseType.MULTIPLE_CHOICE)
                        if res.get('fillblank'): found_types.add(ExerciseType.FILL_BLANK)
                        if res.get('listening'): found_types.add(ExerciseType.LISTENING)
                        if res.get('presentation'): found_types.add(ExerciseType.PRESENTATION)
                except Exception:
                    # Fallback si frame.evaluate falla o si es un mock en pruebas unitarias
                    try:
                        if hasattr(frame, 'content'):
                            content = frame.content()
                            if 'is-radiobutton-voice' in content or 'contentblock--SpeakingAndRecording' in content:
                                found_types.add(ExerciseType.SPEAKING)
                            if 'osSorting' in content or 'os-sorting-element' in content:
                                found_types.add(ExerciseType.SORTING)
                            if 'shuffle_interaction' in content or 'os-sequence-element' in content:
                                found_types.add(ExerciseType.REORDERING)
                            if 'is-linking-lines' in content or 'll_element_view' in content or 'isLinkingMultipleLines' in content or 'matching_interaction' in content:
                                found_types.add(ExerciseType.MATCHING)
                            if 'im-marking__item-button' in content or 'im-marking' in content:
                                found_types.add(ExerciseType.HIGHLIGHTING)
                            if 'im-proofing' in content or 'markable' in content:
                                found_types.add(ExerciseType.PROOFREADING)
                            if 'om-text-gap__droppable' in content:
                                found_types.add(ExerciseType.DRAG_AND_DROP)
                            if 'listbox' in content or 'wrapper-dropdown' in content or 'is-dropdown' in content:
                                found_types.add(ExerciseType.DROPDOWN)
                            if 'type="radio"' in content or 'choice_interaction' in content:
                                found_types.add(ExerciseType.MULTIPLE_CHOICE)
                            if '<input type="text"' in content or 'textGapItem' in content:
                                found_types.add(ExerciseType.FILL_BLANK)
                            if 'pp-present' in content or 'is-presentation' in content:
                                found_types.add(ExerciseType.PRESENTATION)
                    except Exception:
                        pass
            
            # Prioritize types
            if ExerciseType.SPEAKING in found_types: return ExerciseType.SPEAKING
            if ExerciseType.SORTING in found_types: return ExerciseType.SORTING
            if ExerciseType.REORDERING in found_types: return ExerciseType.REORDERING
            if ExerciseType.MATCHING in found_types: return ExerciseType.MATCHING
            if ExerciseType.HIGHLIGHTING in found_types: return ExerciseType.HIGHLIGHTING
            if ExerciseType.PROOFREADING in found_types: return ExerciseType.PROOFREADING
            if ExerciseType.DRAG_AND_DROP in found_types: return ExerciseType.DRAG_AND_DROP
            if ExerciseType.DROPDOWN in found_types: return ExerciseType.DROPDOWN
            if ExerciseType.MULTIPLE_CHOICE in found_types: return ExerciseType.MULTIPLE_CHOICE
            if ExerciseType.FILL_BLANK in found_types: return ExerciseType.FILL_BLANK
            if ExerciseType.PRESENTATION in found_types: return ExerciseType.PRESENTATION
            if ExerciseType.LISTENING in found_types: return ExerciseType.LISTENING
                    
            return ExerciseType.UNKNOWN
        except Exception as e:
            print(f"Error detecting exercise: {e}")
            return ExerciseType.UNKNOWN
