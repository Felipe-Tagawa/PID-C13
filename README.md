# Parte Teórica

## 1. Funcionamento da planta

A planta é um **forno**, em que o objetivo é controlar a temperatura de acordo com um valor de referência definido pelo usuário. No projeto, essa referência é representada por **SP(s)**, enquanto a saída do processo é representada por **PV(s)**.

Por ser um sistema térmico, o forno não responde de forma instantânea. Quando o valor de referência muda, a temperatura leva um tempo para começar a variar e também leva um tempo até se aproximar de um novo valor de equilíbrio. Esse comportamento é compatível com sistemas de primeira ordem, como os sistemas térmicos citados no próprio material do trabalho.

Além disso, o sistema pode apresentar um atraso de transporte, também chamado de tempo morto. Esse atraso representa o tempo entre a aplicação de uma mudança na entrada e o início perceptível da resposta do sistema. Em processos térmicos isso pode acontecer por causa da própria inércia térmica do forno.

No ensaio utilizado para a identificação, é aplicada uma **mudança em degrau no sinal de referência** e a resposta da temperatura é observada ao longo do tempo. A partir dessa curva, são estimados os parâmetros do modelo da planta.

No dataset, a variável `in` representa o **SetPoint**, ou seja, a temperatura desejada para o sistema. A saída representa a temperatura medida do forno. O material também indica que o valor inicial do SetPoint na interface deve ser o mesmo presente no conjunto de dados utilizado.

Em uma aplicação real, a temperatura poderia ser medida por sensores como um **termopar** ou um **PT100**, que são bastante utilizados em sistemas térmicos. Já o aquecimento poderia ser feito por uma resistência elétrica, acionada por algum circuito de potência, como um relé de estado sólido, TRIAC ou outro dispositivo adequado.

De forma simplificada, o funcionamento seria:

**SetPoint → Controlador → Aquecedor → Forno → Sensor de temperatura**

---

## 2. Variáveis do sistema

A **variável controlada** é a temperatura do forno, já que essa é a grandeza que se deseja manter próxima do valor de referência. No sistema em malha fechada, essa temperatura medida é comparada com o SetPoint para gerar o erro utilizado pelo controlador.

O **SetPoint** é a temperatura de referência definida para o sistema. No dataset ele corresponde à variável `in`.

A **variável manipulada** é a ação aplicada ao sistema de aquecimento, ou seja, a potência fornecida à resistência elétrica. É por meio dessa potência que o controlador consegue aumentar ou diminuir a temperatura do forno.

As principais perturbações que podem afetar o sistema são:

- variação da temperatura ambiente;
- abertura da porta do forno;
- entrada ou retirada de materiais;
- variação da carga térmica;
- perdas de calor para o ambiente;
- variações na tensão de alimentação;
- ruídos na medição do sensor.

Essas perturbações podem fazer a temperatura se afastar do valor desejado, fazendo com que o controlador tenha que corrigir novamente a resposta.

Em relação às faixas de operação:

| Grandeza | Tipo | Faixa/condição de operação |
|---|---|---|
| Temperatura do forno | Variável controlada | mínimo e máximo observados no dataset |
| SetPoint | Referência | valores de `in` presentes no dataset |
| Potência do aquecedor | Variável manipulada | conforme o atuador utilizado |
| Temperatura ambiente | Perturbação | depende das condições do ambiente |
| Carga térmica | Perturbação | depende do material inserido no forno |

Assim, o sistema pode ser resumido da seguinte forma:

- **SetPoint:** temperatura desejada;
- **Variável controlada:** temperatura do forno;
- **Variável manipulada:** potência aplicada ao aquecedor;
- **Sensor:** termopar, PT100 ou similar;
- **Atuador:** resistência elétrica com circuito de acionamento;
- **Perturbações:** perdas térmicas, temperatura ambiente, abertura da porta, carga térmica e variações de alimentação.

# Parte Prática

## 3. Comparação e ajuste fino do modelo

Após a identificação da planta pelos métodos de Smith e Sundaresan, o sistema permite comparar a resposta experimental com a resposta obtida pelo modelo FOPDT identificado.

O modelo considerado é:

$$
G(s)=\frac{K}{\tau s+1}e^{-\theta s}
$$

em que:

- **K** representa o ganho do processo;
- **τ** representa a constante de tempo;
- **θ** representa o tempo morto do sistema.

Para uma entrada degrau de amplitude $\Delta u$, a resposta temporal utilizada na etapa de ajuste é:

$$
y(t)=
\begin{cases}
0, & t<\theta \\
K\Delta u\left(1-e^{-\frac{t-\theta}{\tau}}\right), & t\geq\theta
\end{cases}
$$

### Avaliação da aproximação

A qualidade do modelo é avaliada comparando a resposta estimada com os dados experimentais.

O erro em cada instante é dado por:

$$
e_i=y_i-\hat{y}_i
$$

onde $y_i$ corresponde ao valor experimental e $\hat{y}_i$ ao valor estimado pelo modelo.

Como métrica principal, é utilizado o **RMSE** (*Root Mean Squared Error*):

$$
RMSE=
\sqrt{
\frac{1}{n}
\sum_{i=1}^{n}
(y_i-\hat{y}_i)^2
}
$$

Também é apresentado o erro absoluto máximo observado durante o experimento:

$$
E_{\max}=
\max |y_i-\hat{y}_i|
$$

Para facilitar a interpretação do RMSE, ele é comparado com a amplitude total da resposta:

$$
A=y_{\max}-y_{\min}
$$

e:

$$
RMSE_{\%}=
\frac{RMSE}{A}\times100
$$

Como critério auxiliar utilizado na interface:

- **RMSE relativo de até 5%:** aproximação considerada satisfatória;
- **entre 5% e 10%:** aproximação razoável, com possibilidade de melhoria;
- **acima de 10%:** recomenda-se avaliar um ajuste fino dos parâmetros.

> Esses limites são utilizados apenas como referência prática para auxiliar a análise e não representam um critério universal de identificação de sistemas.

---

### Ajuste fino manual

A interface permite modificar individualmente os parâmetros $K$, $\tau$ e $\theta$ por meio de controles deslizantes.

O efeito esperado de cada parâmetro é:

- aumento de **K** → aumenta o valor final da resposta;
- redução de **K** → reduz o valor final da resposta;
- aumento de **τ** → torna a resposta mais lenta;
- redução de **τ** → torna a resposta mais rápida;
- aumento de **θ** → aumenta o atraso para o início da resposta;
- redução de **θ** → faz com que a resposta comece mais cedo.

A curva estimada é recalculada após cada alteração, permitindo observar diretamente o reflexo dos parâmetros sobre a resposta do sistema.

---

### Ajuste automático

Além do ajuste manual, foi implementado um ajuste automático utilizando a função `