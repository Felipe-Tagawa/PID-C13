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