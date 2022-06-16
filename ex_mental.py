#Plantillas de examen mental

def em(plantilla, nombre):
    em_template = {
        'Normal': (f'Encuentro a {nombre} con buena higiene y aliño, edad aparente y real concordantes, vestimenta acorde al clima, alerta, orientado, cooperador y sin alteraciones '+
            f'psicomotrices y/o condcuta alucinada. Se refiere de ánimo "mas o menos (sic {nombre}), afecto eutímico. Discurso espontáneo, fluído, '+
                'coherente, congruente, de velocidad y volumen noramles con una latencia de respsuuesta conservada. Pensamiento lineal sin expresar ideas delirantes, '+
                    'suicidas, homicidas o alteraciones de la sensopercepción. Parcial introspección, juicio dentro del marco de la realidad y buen control de impulsos.'),

        'Depresión': (f'Encuentro a {nombre} con regular higiene y aliño, edad aparente y real concordantes, vestimenta acorde al clima, inatento, orientado en persona y lugar, parcialmente cooperador, apático y con pobre contacto visual, '+
            'hipoactivo y sin condcuta alucinada evidente. Se refiere de ánimo deprimido, afecto hipotímico. Discurso inducido, parco,'+
                'coherente, congruente, bradifémico, volumen bajo y con una latencia de respuesta incrementada. Pensamiento concreto sin expresar ideas delirantes, '+
                    'suicidas, homicidas o alteraciones de la sensopercepción. Parcial introspección, juicio dentro del marco de la realidad y buen control de impulsos.'),

        'Psicosis': f'Encuentro a {nombre} con regular higiene y aliño, edad aparente y real concordantes, vestimenta deteriorada, inatento, orientado en persona, poco cooperador, con pobre contacto visual, '+
            'incapaz de mantenerse en un solo sitio, suspicaz; y sin condcuta alucinada. Se refiere de ánimo eutímico, afecto en ocasiones irascible aunque predominantemente restringido. Discurso inducido, parco, '+
                'coherente, incongruente, bradifémico, volumen normal y con una latencia de respuesta incrementada. Pensamiento tangencial con delirios de tipo , '+
                    'sin ideas suicidas, homicidas o alteraciones de la sensopercepción. Nula introspección, juicio fuera del marco de la realidad y parcial control de impulsos.',

        'Ansiedad': f'Encuentro a {nombre} con buena higiene y aliño, edad aparente y real concordantes, vestimenta acorde al clima, hiperproséxico, orientado en persona,  lugar, tiempo y situación, cooperador, demandante, '+
            'agitación psicomotriz circunscrita a manos y piernas y sin condcuta alucinada evidente. Se refiere de ánimo y afecto ansiosos. Discurso espontáneo, logorréico, '+
                'coherente, congruente, velocidad, volumen latencia de respuesta conservadas. Pensamiento circunstancial sin expresar ideas delirantes, '+
                    'suicidas, homicidas o alteraciones de la sensopercepción. Parcial introspección, juicio dentro del marco de la realidad y buen control de impulsos.',

        'Mania': f'Encuentro a {nombre} con regular higiene y aliño, edad aparente y real concordantes, vestimenta inadecuada para el tiempo y situación, hiperproséxico, parcialmente orientado, nada cooperador, demandante, '+
            'agitación psicomotriz con incapacidad para mantenerse en un solo sitio y con deambulación en el consultorio. No se observa condcuta alucinada. Se refiere de ánimo elevado y afecto hipertímico, expansivo y eventualmente disfórico. Discurso espontáneo, logorréico, '+
                'taquifémico, coherente, incongruente, de difícil interrupción y seguimiento con latencia de respues ausente. Pensamiento taquipsíquico, prolijo y con fuga ideas. Expresa delirios de grandiosidad, '+
                    'no expresa ideas, suicidas, homicidas o alteraciones de la sensopercepción. Nula introspección, juicio demeritado y nulo control de impulsos.',
    }
    selected = em_template[plantilla]
    return selected
    