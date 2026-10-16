
void FUN_0000_2949(void)

{
  int iVar1;
  int in_BX;
  undefined1 *unaff_SI;
  char *unaff_DI;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  
code_r0x00002949:
  do {
    in_BX = in_BX + 1;
  } while (unaff_DI[in_BX] == ' ');
  if (unaff_DI[in_BX] == '=') {
    do {
      in_BX = in_BX + 1;
    } while (unaff_DI[in_BX] == ' ');
    FUN_0100_1722(unaff_DI + in_BX);
  }
  else {
    for (; (in_BX = -1, *unaff_DI != '\0' || (unaff_DI[1] != '\0')); unaff_DI = unaff_DI + 1) {
      do {
        iVar1 = in_BX + 1;
        if (unaff_SI[iVar1] == '\n') goto code_r0x00002949;
        in_BX = iVar1;
      } while (unaff_DI[iVar1] == unaff_SI[iVar1]);
    }
    *unaff_SI = 0;
  }
  return;
}

